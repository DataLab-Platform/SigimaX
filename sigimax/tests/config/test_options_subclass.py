# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""Quick test of SigimaX options subclassing."""

# guitest: show

import pytest

from sigimax.config import SigimaXOptions, TypedOptionField


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


@pytest.mark.unit
def test_options_subclass():
    """Test that SigimaXOptions can be subclassed with custom options."""
    o = MyAppOptions()
    assert len(o.list_options()) > 0
    assert o.rpc_enabled.get(sync_env=False) is True
    assert o.rpc_port.get(sync_env=False) == 8080
    # Inherited option from SigimaXOptions must be accessible
    assert o.color_mode.get(sync_env=False) is not None


if __name__ == "__main__":
    test_options_subclass()
