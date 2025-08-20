import asyncio
from puppemon_py_script.pausable import Pausable
from aiohttp import ClientSession
from dotenv import dotenv_values, load_dotenv
from jsonrpcclient import Error, Ok, parse, request
from py_resymot_client.client_XYZ import Resymot_XYZ
import os
import math


def get_config():
    default_envs = {"RESYMOT_SERVER": "http://localhost:8383", "FEED_RATE": 0.6, "MACH_ID": 1}
    config = {
        **default_envs,
        **dotenv_values(".env"),
        # **os.environ,  # override loaded values with environment variables
    }
    return config

async def user_main():
    config = get_config()

    async with ClientSession() as client:
        xyz = Resymot_XYZ(client, config["RESYMOT_SERVER"], config["MACH_ID"])
        feedrate = float(config["FEED_RATE"])

        await xyz.power_off()
        await xyz.reset()
        assert await xyz.set_to_auto_mode()

        async def user_pause_cb():
            print("user paused 1.")
            await xyz.wait_complete()
            await asyncio.sleep(0)

        async def user_resume_cb():
            print("user resumed 1.")
            await xyz.wait_complete()
            await asyncio.sleep(0)

        # async def user_pause_cb_2():
        #     print("user paused 2.")
        #     await xyz.wait_complete()
        #     await asyncio.sleep(0)

        # async def user_resume_cb_2():
        #     print("user resumed 2.")
        #     await xyz.wait_complete()
        #     await asyncio.sleep(0)

        pausable1 = Pausable(pause_cb=user_pause_cb, resume_cb=user_resume_cb)
        # pausable2 = Pausable(pause_cb=user_pause_cb_2, resume_cb=user_resume_cb_2)

        while True:
            print("Hello world!")
            await xyz.straight_move_to([0.4, 0.0, 0.1], feedrate)
            await xyz.straight_move_to([0.3, 0.2, 0.15], feedrate)
            normal = [0.0, 0.0, 1.0]
            await xyz.arc_move_to([0.4, 0.2, 0], normal, math.pi, feedrate)
            await xyz.straight_move_to([0.5, 0, 0.05], feedrate)
            await xyz.arc_move_to([0.4, 0, 0.1], normal, -math.pi, feedrate)
            assert await xyz.wait_complete()
            await pausable1.maybe_pause()

            # print("World!")
            # await asyncio.sleep(0.5)
            # await pausable2.maybe_pause()


async def user_stop_cb():
    print("Stopping user script...")
    config = get_config()
    async with ClientSession() as client:
        xyz = Resymot_XYZ(client, config["RESYMOT_SERVER"], config["MACH_ID"])
        feedrate = 0.3

        await xyz.wait_complete()
        cur_pos = await xyz.curr_pos()

        new_pos = cur_pos
        new_pos[2] = 0.5
        await xyz.straight_move_to(new_pos, feedrate)
        await xyz.wait_complete()
        await xyz.power_off()


if __name__ == "__main__":
    # This is for standalone testing of the user script,
    # the real entrypoint is __main__.py
    from puppemon_py_script.pausable import PausableController

    controller = PausableController()
    Pausable.set_controller(controller)
    asyncio.run(user_main())
