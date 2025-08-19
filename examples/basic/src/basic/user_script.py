import asyncio
from puppemon_py_script.pausable import Pausable


async def user_main():
    # Create two different pausable instances with different callbacks
    async def user_pause_cb():
        print("user paused 1.")
        await asyncio.sleep(0)

    async def user_resume_cb():
        print("user resumed 1.")
        await asyncio.sleep(0)

    async def user_pause_cb_2():
        print("user paused 2.")
        await asyncio.sleep(0)

    async def user_resume_cb_2():
        print("user resumed 2.")
        await asyncio.sleep(0)

    pausable1 = Pausable(pause_cb=user_pause_cb, resume_cb=user_resume_cb)
    pausable2 = Pausable(pause_cb=user_pause_cb_2, resume_cb=user_resume_cb_2)

    while True:
        print("Hello")
        await asyncio.sleep(0.5)
        await pausable1.maybe_pause()
        print("World!")
        await asyncio.sleep(0.5)
        await pausable2.maybe_pause()


async def user_stop_cb():
    print("user stopped.")
    await asyncio.sleep(0)


if __name__ == "__main__":
    # This is for standalone testing of the user script,
    # the real entrypoint is __main__.py
    from puppemon_py_script.pausable import PausableController

    controller = PausableController()
    Pausable.set_controller(controller)
    asyncio.run(user_main())
