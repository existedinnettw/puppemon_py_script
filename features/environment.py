import asyncio
import contextlib


def before_all(context):
    context.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(context.loop)


def after_all(context):
    loop = getattr(context, "loop", None)
    if not loop:
        return
    try:
        if not loop.is_closed():
            asyncio.set_event_loop(loop)
            pending = asyncio.all_tasks()
            for task in pending:
                task.cancel()
            with contextlib.suppress(Exception):
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    finally:
        if not loop.is_closed():
            loop.close()
