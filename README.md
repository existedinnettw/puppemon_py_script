# puppemon_py_script

A scripting framework open to end user to ensure following puppemon requirement.

## build

First, generate grpc code with

```bash
# cd py project folder first
uv run python -m grpc_tools.protoc --proto_path=protos --python_out=src/puppemon_py_script/generated --grpc_python_out=src/puppemon_py_script/generated protos/*.proto
```

Then, it is recommended to check out examples to see how to use the framework in practice.

```bash
cd examples/basic
uv run python -m basic
```

For tests,

```bash
uv run behave
```
