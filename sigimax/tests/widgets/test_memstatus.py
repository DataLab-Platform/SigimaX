# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Memory status widget application test
"""

# guitest: show

import psutil
import pytest

from sigimax import config
from sigimax.env import execenv
from sigimax.tests import sigimax_test_app_context

pytestmark = pytest.mark.app


def memory_alarm(threshold, expect_alarm):
    """Memory alarm test

    Args:
        threshold: available memory threshold (MB)
        expect_alarm: True if alarm is expected to trigger
    """
    config.CONF.available_memory_threshold.set(threshold)
    with sigimax_test_app_context() as win:
        alarm_states = []
        win.memorystatus.SIG_MEMORY_ALARM.connect(alarm_states.append)
        win.memorystatus.update_status()  # Force memory status update
        assert len(alarm_states) == 1, "SIG_MEMORY_ALARM should have been emitted once"
        alarm_fired = alarm_states[0]
        assert alarm_fired == expect_alarm, (
            f"Expected alarm={expect_alarm} for threshold={threshold} MB, "
            f"got alarm={alarm_fired}"
        )
        # Verify visual indicators match alarm state
        if expect_alarm:
            assert "red" in win.memorystatus.label.styleSheet()
        else:
            assert "red" not in win.memorystatus.label.styleSheet()
        execenv.print(f"        Alarm fired: {alarm_fired} (expected: {expect_alarm})")


def test_mem_status():
    """Memory alarm test"""
    mem_available = psutil.virtual_memory().available // (1024**2)
    execenv.print(f"Memory status widget test (memory available: {mem_available} MB):")
    test_cases = (
        (mem_available * 2, True),  # Threshold above available → alarm ON
        (mem_available - 100, False),  # Threshold below available → alarm OFF
    )
    for index, (threshold, expect_alarm) in enumerate(test_cases):
        execenv.print(
            f"    Threshold {index}: {threshold} MB (expect alarm: {expect_alarm})"
        )
        memory_alarm(threshold, expect_alarm)
    config.CONF.reset_to_defaults()


if __name__ == "__main__":
    test_mem_status()
