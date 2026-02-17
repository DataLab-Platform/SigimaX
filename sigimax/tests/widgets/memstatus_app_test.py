# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Memory status widget application test
"""

# guitest: show

import psutil

from sigimax import config
from sigimax.env import execenv
from sigimax.tests import sigimax_test_app_context


def memory_alarm(threshold):
    """Memory alarm test"""
    config.Conf.main.available_memory_threshold.set(threshold)
    with sigimax_test_app_context() as win:
        win.memorystatus.update_status()  # Force memory status update
        # TODO : Add large data allocation to trigger the alarm


def test_mem_status():
    """Memory alarm test"""
    mem_available = psutil.virtual_memory().available // (1024**2)
    execenv.print(f"Memory status widget test (memory available: {mem_available} MB):")
    for index, threshold in enumerate((mem_available * 2, mem_available - 100)):
        execenv.print(f"    Threshold {index}: {threshold} MB")
        memory_alarm(threshold)
    config.reset()


if __name__ == "__main__":
    test_mem_status()
