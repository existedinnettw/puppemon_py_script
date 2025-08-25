import asyncio
import os
import signal
import threading

import grpc
import inspect
from .generated import script_pb2_grpc
from google.protobuf import empty_pb2
from .pausable import PausableController


class ScriptServicer(script_pb2_grpc.ScriptServicer):
    def __init__(
        self,
        pausable_controller: PausableController,
        user_main_task: asyncio.Task,
        user_stop_cb,
        *,
        kill_on_stop: bool = True,
    ):
        self._pausable_controller = pausable_controller
        self._user_main_task = user_main_task
        self._user_stop_cb = user_stop_cb
        self._kill_on_stop = kill_on_stop
        self.terminating = False

    async def Stop(self, request, context):  # noqa: N802 (gRPC naming)
        print("[DEBUG] ScriptServicer: Stop received")
        self._user_main_task.cancel()
        if self._user_stop_cb:
            result = self._user_stop_cb()
            if inspect.isawaitable(result):
                await result
        if self._kill_on_stop and not self.terminating:
            self.terminating = True
            threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
        return empty_pb2.Empty()

    async def Pause(self, request, context: grpc.ServicerContext):  # noqa: N802
        print("[DEBUG] ScriptServicer: Pause received")
        self._pausable_controller.pause()

        # If a timeout is specified, schedule an auto-resume after the duration
        timeout_ms = getattr(request, "timeout_millis", 0) or 0
        # Try to coordinate and wait until all expected tasks have reached a pausable point
        # The controller will succeed immediately if not configured with an expected count
        all_paused = await self._pausable_controller.wait_all_paused(
            timeout=(timeout_ms / 1000.0) if timeout_ms > 0 else None
        )
        # print(f"[DEBUG] all_paused: {all_paused}")
        if not all_paused and timeout_ms > 0:
            # Abort the pause per requirement and report timeout to client
            self._pausable_controller.resume()
            await asyncio.sleep(0)  # yield to let any paused tasks wake
            context.set_details("pause timed out")
            context.set_code(grpc.StatusCode.DEADLINE_EXCEEDED)

        return empty_pb2.Empty()

    async def Resume(self, request, context):  # noqa: N802
        print("[DEBUG] ScriptServicer: Resume received")
        self._pausable_controller.resume()
        return empty_pb2.Empty()
