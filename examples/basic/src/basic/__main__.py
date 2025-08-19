import asyncio
import argparse
import grpc

from .user_script import user_main, user_stop_cb
from puppemon_py_script import ScriptServicer, script_pb2_grpc
from puppemon_py_script.pausable import Pausable, PausableController


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=51052, help="Port for the gRPC server")
    args = parser.parse_args()

    # Create and set the central controller
    pausable_controller = PausableController()
    Pausable.set_controller(pausable_controller)

    user_main_task = asyncio.create_task(user_main())

    server = grpc.aio.server()
    servicer = ScriptServicer(pausable_controller, user_main_task, user_stop_cb)
    script_pb2_grpc.add_ScriptServicer_to_server(servicer, server)
    server.add_insecure_port(f"localhost:{args.port}")

    print(f"Script server started on localhost:{args.port}")
    await server.start()

    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        print("Server stopped by user")
        await server.stop(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
