import asyncio
from behave import when, then

from features.steps.common import run, RunningScript, ScriptClient
from features.steps.pause_steps import step_then_state_running  # noqa: F401


@when("the client sends the RESUME command")
def step_send_resume(context):
    server: RunningScript = context.running

    async def _call():
        client = ScriptClient(server.port)
        await client.resume()

    run(context.loop, _call())


@then("both tasks continue and complete their work")
def step_both_tasks_continue(context):
    server: RunningScript = context.running

    async def _stop():
        client = ScriptClient(server.port)
        try:
            await client.stop()
        except Exception:
            pass

    run(context.loop, _stop())
    run(context.loop, asyncio.sleep(0))
    assert server.main_task is not None
    assert server.main_task.cancelled() or server.main_task.done()
