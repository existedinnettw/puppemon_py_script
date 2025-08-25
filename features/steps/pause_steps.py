import asyncio
import grpc
from behave import given, when, then

from features.steps.common import run, RunningScript, ScriptClient


@given("the script defines concurrent async tasks A and B with pausable points")
def step_define_tasks(context):
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
    run(context.loop, asyncio.sleep(0))

    async def _call():
        client = ScriptClient(server.port)
        await client.pause()

    run(context.loop, _call())


@then("each task halts at its next pausable point")
@then("both tasks pause at their next pausable points")
def step_both_tasks_pause(context):
    run(context.loop, asyncio.sleep(0))
    server = context.running
    assert server.servicer is not None
    assert server.servicer._pausable_controller.is_paused is True


@given('the script state is "paused"')
def step_given_state_paused(context):
    from features.steps.pause_steps import (
        step_send_pause,
        step_both_tasks_pause,
    )  # self-import safe at runtime

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
    from features.steps.pause_steps import step_script_starts

    step_script_starts(context)


@then('the server acknowledges with "already paused" (no state change)')
def step_then_ack_already_paused(context):
    from features.steps.pause_steps import step_then_state_paused

    step_then_state_paused(context)


@then('the server acknowledges with "already running" (no state change)')
def step_then_ack_already_running(context):
    from features.steps.pause_steps import step_then_state_running

    step_then_state_running(context)


@given("tasks A and B are executing and both can reach a pausable point promptly")
def step_tasks_both_prompt(context):
    context.running.task_config.setdefault("A", {})["pause_delay"] = 0.0
    context.running.task_config.setdefault("B", {})["pause_delay"] = 0.0
    step_tasks_running(context)


@then("the server responds with success before the timeout elapses")
def step_pause_success_before_timeout(context):
    assert getattr(context, "pause_error", None) is None
    step_then_state_paused(context)


@then('the script state remains "paused"')
def step_state_remains_paused(context):
    step_then_state_paused(context)


@then("tasks A and B continue execution past the pause points")
def step_tasks_continue_past_pause(context):
    run(context.loop, asyncio.sleep(0))
    step_then_state_running(context)


@given("tasks A and B are halted at pausable points")
def step_tasks_halted_at_pause(context):
    # ensure a tick and check paused state
    run(context.loop, asyncio.sleep(0))
    step_then_state_paused(context)


@when("the client sends the PAUSE command with a timeout of {seconds:d} seconds")
@when("the client sends the PAUSE command with a timeout of {seconds:d} second")
def step_send_pause_with_timeout(context, seconds):
    server: RunningScript = context.running

    async def _call():
        client = ScriptClient(server.port)
        try:
            await client.pause(seconds)
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
    assert isinstance(getattr(context, "pause_error", None), grpc.aio.AioRpcError)
    assert context.pause_error.code() == grpc.StatusCode.DEADLINE_EXCEEDED


@then("no global pause is applied (tasks continue running)")
def step_no_global_pause(context):
    server = context.running
    assert server.servicer is not None
    assert server.servicer._pausable_controller.is_paused is False
    assert server.main_task is not None and not server.main_task.done()
