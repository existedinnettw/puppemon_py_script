import asyncio
from dataclasses import dataclass, field
from typing import Dict

import grpc
from google.protobuf import empty_pb2

from puppemon_py_script import ScriptServicer, script_pb2_grpc
from puppemon_py_script.pausable import Pausable, PausableController
from puppemon_py_script.generated import script_pb2


def run(loop: asyncio.AbstractEventLoop, coro):
    return loop.run_until_complete(coro)


class ScriptClient:
    def __init__(self, port: int):
        self._addr = f"127.0.0.1:{port}"

    async def pause(self, timeout_seconds: int | None = None):
        PR = getattr(script_pb2, "PauseRequest")
        async with grpc.aio.insecure_channel(self._addr) as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            if timeout_seconds is None:
                return await stub.Pause(PR())
            return await stub.Pause(PR(timeout_millis=int(timeout_seconds * 1000)))

    async def resume(self):
        async with grpc.aio.insecure_channel(self._addr) as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            return await stub.Resume(empty_pb2.Empty())

    async def stop(self):
        async with grpc.aio.insecure_channel(self._addr) as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            return await stub.Stop(empty_pb2.Empty())

    async def call_unknown(self) -> bool:
        async with grpc.aio.insecure_channel(self._addr) as channel:
            method = channel.unary_unary("/script.Script/Unknown")
            try:
                await method(b"")
            except grpc.aio.AioRpcError as e:
                return e.code() == grpc.StatusCode.UNIMPLEMENTED
            return False


@dataclass
class RunningScript:
    server: grpc.aio.Server | None
    servicer: ScriptServicer | None
    main_task: asyncio.Task | None
    port: int
    controller: PausableController
    stop_event: asyncio.Event
    task_config: Dict[str, Dict[str, float]] = field(default_factory=dict)


async def _run_dummy_tasks(running: RunningScript):
    controller = running.controller
    stop_event = running.stop_event
    Pausable.set_controller(controller)

    async def task(name: str):
        with Pausable(name=name) as p:
            while not stop_event.is_set():
                await asyncio.sleep(0)
                cfg = running.task_config.get(name, {})
                delay = float(cfg.get("pause_delay", 0.0))
                if delay > 0:
                    await asyncio.sleep(delay)
                await p.maybe_pause()
                await asyncio.sleep(0)

    await asyncio.gather(task("A"), task("B"))


async def start_server_with_tasks(loop: asyncio.AbstractEventLoop) -> RunningScript:
    controller = PausableController()
    stop_event = asyncio.Event()
    dummy = RunningScript(
        server=None,
        servicer=None,
        main_task=None,
        port=0,
        controller=controller,
        stop_event=stop_event,
    )

    main_task = loop.create_task(_run_dummy_tasks(dummy))
    dummy.main_task = main_task

    server = grpc.aio.server()
    servicer = ScriptServicer(
        controller, main_task, user_stop_cb=lambda: stop_event.set(), kill_on_stop=False
    )
    script_pb2_grpc.add_ScriptServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    dummy.server = server
    dummy.servicer = servicer
    dummy.port = port
    return dummy
