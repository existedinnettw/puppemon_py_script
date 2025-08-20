import asyncio

# TODO try relative import
from py_resymot_demo.user_script import user_main, user_stop_cb
from puppemon_py_script import default_main

if __name__ == "__main__":
    try:
        asyncio.run(default_main(user_main, user_stop_cb))
    except KeyboardInterrupt:
        pass
