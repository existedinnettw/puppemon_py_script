import asyncio
import contextlib


def before_all(context):
    context.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(context.loop)


def after_scenario(context, scenario):
    loop = getattr(context, "loop", None)
    running = getattr(context, "running", None)
    if not loop or not running:
        return

    async def _cleanup_running():
        # Signal tasks to stop if still running
        try:
            if getattr(running, "stop_event", None) is not None:
                running.stop_event.set()
        except Exception:
            pass
        # Cancel user main task if still alive
        try:
            if getattr(running, "main_task", None) and not running.main_task.done():
                running.main_task.cancel()
        except Exception:
            pass
        # Stop gRPC server gracefully
        try:
            if getattr(running, "server", None) is not None:
                await running.server.stop(0)
                with contextlib.suppress(Exception):
                    await running.server.wait_for_termination()
        except Exception:
            pass

    asyncio.set_event_loop(loop)
    with contextlib.suppress(Exception):
        loop.run_until_complete(_cleanup_running())
    # Clear reference
    try:
        context.running = None
    except Exception:
        pass


def after_all(context):
    loop = getattr(context, "loop", None)
    if not loop or loop.is_closed():
        return

    async def _shutdown():
        # Cancel all tasks except this current one
        current = asyncio.current_task()
        tasks = [t for t in asyncio.all_tasks() if t is not current]
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*tasks, return_exceptions=True)
        # Give tasks a moment to finalize
        with contextlib.suppress(Exception):
            await asyncio.sleep(0)
        # Shutdown async generators & default executor
        with contextlib.suppress(Exception):
            await loop.shutdown_asyncgens()
        with contextlib.suppress(Exception):
            await loop.shutdown_default_executor()

    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_shutdown())
    finally:
        with contextlib.suppress(Exception):
            loop.close()
