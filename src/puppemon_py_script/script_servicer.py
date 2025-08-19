import asyncio
import os
import signal
import threading

from .generated import script_pb2_grpc
from google.protobuf import empty_pb2
from .pausable import PausableController


class ScriptServicer(script_pb2_grpc.ScriptServicer):
    def __init__(
        self, pausable_controller: PausableController, user_main_task: asyncio.Task, user_stop_cb
    ):
        self._pausable_controller = pausable_controller
        self._user_main_task = user_main_task
        self._user_stop_cb = user_stop_cb
        self.terminating = False
        # Task scheduled to auto-resume after a pause timeout (if any)
        self._auto_resume_task = None

    async def Stop(self, request, context):  # noqa: N802 (gRPC naming)
        print("ScriptServicer: Stop received")
        if self._user_stop_cb:
            await self._user_stop_cb()
        self._user_main_task.cancel()
        if not self.terminating:
            self.terminating = True
            threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
        return empty_pb2.Empty()

    async def Pause(self, request, context):  # noqa: N802
        print("ScriptServicer: Pause received")
        self._pausable_controller.pause()

        # If a timeout is specified, schedule an auto-resume after the duration
        timeout_ms = getattr(request, "timeout_millis", 0) or 0
        if timeout_ms > 0:
            # Cancel any previous auto-resume task to avoid stacking resumes
            if self._auto_resume_task and not self._auto_resume_task.done():
                self._auto_resume_task.cancel()

            async def _auto_resume_after_delay(delay_ms: int):
                try:
                    await asyncio.sleep(delay_ms / 1000.0)
                    self._pausable_controller.resume()
                except asyncio.CancelledError:
                    pass

            self._auto_resume_task = asyncio.create_task(_auto_resume_after_delay(timeout_ms))

        return empty_pb2.Empty()

    async def Resume(self, request, context):  # noqa: N802
        print("ScriptServicer: Resume received")
        if self._auto_resume_task and not self._auto_resume_task.done():
            self._auto_resume_task.cancel()
        self._pausable_controller.resume()
        return empty_pb2.Empty()
