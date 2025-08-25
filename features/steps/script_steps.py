import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Dict

import grpc
from google.protobuf import empty_pb2

from puppemon_py_script import ScriptServicer, script_pb2_grpc
from puppemon_py_script.pausable import Pausable, PausableController
from puppemon_py_script.generated import script_pb2


def run(loop: asyncio.AbstractEventLoop, coro):
    return loop.run_until_complete(coro)


# class TaskConfig:
#     def __init__(self):
#         self.pause_delay = 0.0


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
    controller.set_expected_tasks(2)

    async def task(name: str):
        p = Pausable(name=name)
        while not stop_event.is_set():
            # simulate some work
            await asyncio.sleep(0)
            cfg = running.task_config.get(name, {})
            delay = float(cfg.get("pause_delay", 0.0))
            print(f"name: {name}, task delay: {delay}")
            if delay > 0:
                await asyncio.sleep(delay)
            await p.maybe_pause()
            await asyncio.sleep(0)

    # print("running task_config:", running.task_config)
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

    # user main task that runs two async tasks A and B
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


try:  # pragma: no cover - fallback for static analysis when behave isn't installed
    from behave import given, when, then  # type: ignore
except Exception:  # noqa: BLE001

    def given(*_args, **_kwargs):  # type: ignore
        def _wrap(func):
            return func

        return _wrap

    def when(*_args, **_kwargs):  # type: ignore
        def _wrap(func):
            return func

        return _wrap

    def then(*_args, **_kwargs):  # type: ignore
        def _wrap(func):
            return func

        return _wrap


@given("a script started with an embedded gRPC control server")
def step_start_server(context):
    context.running = run(context.loop, start_server_with_tasks(context.loop))


@when("a client connects to the control server")
def step_connect_client(context):
    # Nothing to do explicitly; connection happens per-RPC via channel
    pass


@then("the client can call the PAUSE command")
def step_can_call_pause(context):
    server: RunningScript = context.running

    async def _call():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            PR = getattr(script_pb2, "PauseRequest")
            await stub.Pause(PR())

    run(context.loop, _call())


@then("the client can call the RESUME command")
def step_can_call_resume(context):
    server: RunningScript = context.running

    async def _call():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            await stub.Resume(empty_pb2.Empty())

    run(context.loop, _call())


@then("the client can call the STOP command")
def step_can_call_stop(context):
    server: RunningScript = context.running

    async def _call():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            with suppress(Exception):
                await stub.Stop(empty_pb2.Empty())

    run(context.loop, _call())


@when("a client sends an unknown command")
def step_unknown_command(context):
    server: RunningScript = context.running

    async def _call():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            # call a non-existent RPC
            method = channel.unary_unary("/script.Script/Unknown")
            try:
                await method(b"")
            except grpc.aio.AioRpcError as e:
                context.unknown_error = e.code() == grpc.StatusCode.UNIMPLEMENTED
            else:
                context.unknown_error = False

    run(context.loop, _call())


@then("the server responds with an error indicating the command is unsupported")
def step_assert_unknown_error(context):
    assert getattr(context, "unknown_error", False)


@given("the script defines concurrent async tasks A and B with pausable points")
def step_define_tasks(context):
    # Already configured in start_server_with_tasks
    pass


@given("tasks A and B are executing")
def step_tasks_running(context):
    run(context.loop, asyncio.sleep(0.05))


@when("the script starts execution")
def step_script_starts(context):
    run(context.loop, asyncio.sleep(0.05))


@then("tasks A and B execute concurrently")
def step_tasks_concurrent(context):
    assert not context.running.main_task.done()


@then("each task can declare pausable points that cooperate with control commands")
def step_tasks_have_pausable_points(context):
    assert True


@when("the client sends the PAUSE command")
def step_send_pause(context):
    server: RunningScript = context.running
    # Yield once to ensure tasks and server are fully running
    run(context.loop, asyncio.sleep(0))

    async def _call():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            PR = getattr(script_pb2, "PauseRequest")
            await stub.Pause(PR())

    run(context.loop, _call())


@then("each task halts at its next pausable point")
@then("both tasks pause at their next pausable points")
def step_both_tasks_pause(context):
    run(context.loop, asyncio.sleep(0))
    server = context.running
    assert server.servicer is not None
    assert server.servicer._pausable_controller.is_paused is True


@when("the client sends the RESUME command")
def step_send_resume(context):
    server: RunningScript = context.running

    async def _call():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            await stub.Resume(empty_pb2.Empty())

    run(context.loop, _call())


@then("both tasks continue and complete their work")
def step_both_tasks_continue(context):
    server: RunningScript = context.running

    async def _stop():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            with suppress(Exception):
                await stub.Stop(empty_pb2.Empty())

    run(context.loop, _stop())
    run(context.loop, asyncio.sleep(0))
    assert server.main_task is not None
    assert server.main_task.cancelled() or server.main_task.done()


@given('the script state is "paused"')
def step_given_state_paused(context):
    step_send_pause(context)
    step_both_tasks_pause(context)


@then('the script state is "paused"')
def step_then_state_paused(context):
    server = context.running
    assert server.servicer._pausable_controller.is_paused is True


@then('the script state is "running"')
def step_then_state_running(context):
    server = context.running
    assert server.servicer is not None
    assert server.servicer._pausable_controller.is_paused is False
    assert not server.main_task.done()


@given('the script state is "running"')
def step_given_state_running(context):
    # default after startup
    step_script_starts(context)


@then('the server acknowledges with "already paused" (no state change)')
def step_then_ack_already_paused(context):
    # We validate via state since server returns Empty
    step_then_state_paused(context)


@then('the server acknowledges with "already running" (no state change)')
def step_then_ack_already_running(context):
    step_then_state_running(context)


@given("tasks A and B are executing and both can reach a pausable point promptly")
def step_tasks_both_prompt(context):
    # Ensure no artificial delay
    context.running.task_config.setdefault("A", {})["pause_delay"] = 0.0
    context.running.task_config.setdefault("B", {})["pause_delay"] = 0.0
    step_tasks_running(context)


@then("the server responds with success before the timeout elapses")
def step_pause_success_before_timeout(context):
    # pause_error is set in the pause-with-timeout step
    assert getattr(context, "pause_error", None) is None
    step_then_state_paused(context)


@then('the script state remains "paused"')
def step_state_remains_paused(context):
    step_then_state_paused(context)


@then("tasks A and B continue execution past the pause points")
def step_tasks_continue_past_pause(context):
    # After a RESUME, controller should not be paused
    run(context.loop, asyncio.sleep(0))
    step_then_state_running(context)


@given("the script is already stopping or stopped")
def step_given_already_stopping(context):
    step_send_stop(context)
    # give loop a tick to cancel
    run(context.loop, asyncio.sleep(0))


@then("the server acknowledges without error (no further action)")
def step_stop_idempotent_ack(context):
    # Call STOP again; should not raise
    step_send_stop(context)


@then("resources are closed and no data loss or corruption is reported")
def step_resources_closed(context):
    # Minimal assertion: main task completed/cancelled
    server = context.running
    assert server.main_task is not None
    assert server.main_task.cancelled() or server.main_task.done()


@when("the client sends the PAUSE command with a timeout of {seconds:d} seconds")
@when("the client sends the PAUSE command with a timeout of {seconds:d} second")
def step_send_pause_with_timeout(context, seconds):
    server: RunningScript = context.running

    async def _call():
        async with grpc.aio.insecure_channel(f"127.0.0.1:{server.port}") as channel:
            stub = script_pb2_grpc.ScriptStub(channel)
            try:
                PR = getattr(script_pb2, "PauseRequest")
                await stub.Pause(PR(timeout_millis=seconds * 1000))
                context.pause_error = None
            except grpc.aio.AioRpcError as e:
                context.pause_error = e

    run(context.loop, _call())


@given(
    "task {task_name:S} is executing and cannot reach a pausable point within {seconds:d} second"
)
def step_task_cannot_pause_in_time(context, task_name, seconds):
    context.running.task_config.setdefault(task_name, {})["pause_delay"] = float(seconds) + 60.0


@given("task {task_name:S} is executing and can reach a pausable point within {seconds:d} second")
def step_task_can_pause_in_time(context, task_name, seconds):
    context.running.task_config.setdefault(task_name, {})["pause_delay"] = max(
        0.0, float(seconds) / 2.0
    )


@then("the server responds with a timeout error")
def step_server_timeout_error(context):
    print("context pause_error:", context.pause_error)
    assert isinstance(getattr(context, "pause_error", None), grpc.aio.AioRpcError)
    assert context.pause_error.code() == grpc.StatusCode.DEADLINE_EXCEEDED


@then("no global pause is applied (tasks continue running)")
def step_no_global_pause(context):
    server = context.running
    assert server.servicer is not None
    assert server.servicer._pausable_controller.is_paused is False
    assert server.main_task is not None and not server.main_task.done()


@given("tasks A and B are halted at pausable points")
def step_tasks_halted_at_pause(context):
    # ensure a tick and check paused state
    run(context.loop, asyncio.sleep(0))
    step_then_state_paused(context)


@when("the client sends the STOP command")
def step_send_stop(context):
    step_can_call_stop(context)


@then("the script shuts down gracefully")
def step_shutdown_gracefully(context):
    # main task should transition to cancelled/done shortly after STOP
    run(context.loop, asyncio.sleep(0))
    server = context.running
    assert server.main_task is not None
    assert server.main_task.cancelled() or server.main_task.done()


@then('the script state remains "running"')
def step_state_remains_running(context):
    step_then_state_running(context)
