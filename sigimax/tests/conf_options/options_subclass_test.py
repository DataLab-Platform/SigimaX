# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""Quick test of SigimaX options subclassing."""

# guitest: show

from sigimax.options import SigimaXOptions, TypedOptionField


class MyAppOptions(SigimaXOptions):
    """
    Docstring for MyAppOptions
    """

    ENV_VAR = "MYAPP_JSON"
    APP_NAME = "MyApp"

    def __init__(self):
        super().__init__()
        self.rpc_enabled = TypedOptionField(
            self,
            "rpc_enabled",
            default=True,
            expected_type=bool,
            description="RPC server",
        )
        self.rpc_port = TypedOptionField(
            self, "rpc_port", default=8080, expected_type=int, description="RPC port"
        )


o = MyAppOptions()
print(f"Total options: {len(o.list_options())}")
print(f"rpc_enabled = {o.rpc_enabled.get(sync_env=False)}")
print(f"rpc_port = {o.rpc_port.get(sync_env=False)}")
print(f"color_mode = {o.color_mode.get(sync_env=False)}")
print("Subclass OK")
