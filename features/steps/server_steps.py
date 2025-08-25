from behave import given, when, then

from features.steps.common import run, start_server_with_tasks, RunningScript, ScriptClient


@given("a script started with an embedded gRPC control server")
def step_start_server(context):
    context.running = run(context.loop, start_server_with_tasks(context.loop))


@when("a client connects to the control server")
def step_connect_client(context):
    pass


@then("the client can call the PAUSE command")
def step_can_call_pause(context):
    server: RunningScript = context.running

    async def _call():
        client = ScriptClient(server.port)
        await client.pause()

    run(context.loop, _call())


@then("the client can call the RESUME command")
def step_can_call_resume(context):
    server: RunningScript = context.running

    async def _call():
        client = ScriptClient(server.port)
        await client.resume()

    run(context.loop, _call())


@then("the client can call the STOP command")
def step_can_call_stop(context):
    server: RunningScript = context.running

    async def _call():
        client = ScriptClient(server.port)
        try:
            await client.stop()
        except Exception:
            pass

    run(context.loop, _call())


@when("a client sends an unknown command")
def step_unknown_command(context):
    server: RunningScript = context.running

    async def _call():
        client = ScriptClient(server.port)
        context.unknown_error = await client.call_unknown()

    run(context.loop, _call())


@then("the server responds with an error indicating the command is unsupported")
def step_assert_unknown_error(context):
    assert getattr(context, "unknown_error", False)
