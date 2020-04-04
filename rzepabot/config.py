# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from os import environ
from pathlib import Path

from discord.ext.commands import BadArgument, MissingRequiredArgument
from pendulum import now, set_locale
from pendulum.helpers import Locale

from rzepabot.pendulum_locale import locale

Locale._cache["pl"] = Locale("pl", locale)
set_locale("pl")

RZEPABOT_ROOT = Path(__file__).parent.parent
RZEPABOT_PREFIX = environ.get(
    "RZEPABOT_DB", str(RZEPABOT_ROOT / "rzepabot.db")
)
DB_PATH = environ.get("RZEPABOT_DB", str(RZEPABOT_ROOT / "rzepabot.db"))
tznow_dt = lambda: now("Europe/Warsaw")
tznow_t = lambda: now("Europe/Warsaw").time()
RZEPABOT_PERMS = 379968


def depoliszifaj(s: str) -> str:
    return str.translate(
        s,
        str.maketrans(
            {
                "Ą": "A",
                "Ć": "C",
                "Ę": "E",
                "Ł": "L",
                "Ń": "N",
                "Ó": "O",
                "Ś": "S",
                "Ź": "Z",
                "Ż": "Ż",
                "ą": "a",
                "ć": "c",
                "ę": "e",
                "ł": "l",
                "ń": "n",
                "ó": "o",
                "ś": "s",
                "ź": "z",
                "ż": "ż",
            }
        ),
    )
