# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX Configuration utilities
"""

from __future__ import annotations

from guidata.userconfig import UserConfig


class AppUserConfig(UserConfig):
    """Application user configuration"""

    def to_dict(self) -> dict:
        """Return configuration as a dictionary"""
        confdict = {}
        for section in self.sections():
            secdict = {}
            for option, value in self.items(section, raw=self.raw):
                secdict[option] = value
            confdict[section] = secdict
        return confdict


CONF = AppUserConfig({})


class Configuration:
    """Configuration file"""

    @classmethod
    def initialize(cls, name: str, version: str, load: bool) -> None:
        """Initialize configuration"""
        CONF.set_application(name, version, load=load)

    @classmethod
    def reset(cls) -> None:
        """Reset configuration"""
        global CONF  # pylint: disable=global-statement
        CONF.cleanup()  # Remove configuration file
        CONF = AppUserConfig({})

    @classmethod
    def get_filename(cls) -> str:
        """Return configuration file name"""
        return CONF.filename()

    @classmethod
    def get_path(cls, basename: str) -> str:
        """Return filename path inside configuration directory"""
        return CONF.get_path(basename)

    @classmethod
    def to_dict(cls) -> dict:
        """Return configuration as a dictionary"""
        return CONF.to_dict()
