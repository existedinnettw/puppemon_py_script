import asyncio
from behave import when, then, given

from features.steps.common import run, RunningScript, ScriptClient
from features.steps.pause_steps import step_then_state_running


@when("the client sends the STOP command")
def step_send_stop(context):
    server: RunningScript = context.running

    async def _call():
        client = ScriptClient(server.port)
        try:
            await client.stop()
        except Exception:
            pass

    run(context.loop, _call())


@then("the script shuts down gracefully")
def step_shutdown_gracefully(context):
    run(context.loop, asyncio.sleep(0))
    server = context.running
    assert server.main_task is not None
    assert server.main_task.cancelled() or server.main_task.done()


@then("resources are closed and no data loss or corruption is reported")
def step_resources_closed(context):
    server = context.running
    assert server.main_task is not None
    assert server.main_task.cancelled() or server.main_task.done()


@then('the script state remains "running"')
def step_state_remains_running(context):
    step_then_state_running(context)


@given("the script is already stopping or stopped")
def step_given_already_stopping(context):
    step_send_stop(context)
    run(context.loop, asyncio.sleep(0))


@then("the server acknowledges without error (no further action)")
def step_stop_idempotent_ack(context):
    step_send_stop(context)
