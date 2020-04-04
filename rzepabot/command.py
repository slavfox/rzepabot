# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from discord.ext.commands import Command


class RzepabotCommand(Command):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)
