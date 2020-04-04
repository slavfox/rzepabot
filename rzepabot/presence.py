# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations
from typing import List

import random
from datetime import datetime, timedelta

from discord import (
    Activity,
    ActivityType,
    CustomActivity,
    Game,
    PartialEmoji,
    BaseActivity,
)

SONGS = []

DEFAULT: List[BaseActivity] = [Game("Animal Crossing: New Horizons")] * 10
DEFAULT.extend(
    [
        Activity(name="Bubblegum K.K.", type=ActivityType.listening.value),
        Activity(name="Go K.K. Rider", type=ActivityType.listening.value),
        Activity(name="DJ K.K.", type=ActivityType.listening.value),
        Activity(name="K.K. Jazz", type=ActivityType.listening.value),
        Game("łowi ryby"),
        Game("łowi ryby"),
        Game("łowi ryby"),
        Game("łapie robaki"),
        Game("łapie robaki"),
        Game("łapie robaki"),
        Game("craftuje patelnie"),
        Game("craftuje patelnie"),
        Game("spłaca długi"),
        Game("spłaca długi"),
    ]
)

_prices_activity = Activity(
    name="notowania rzepy",
    emoji={"id": None, "name": "📉"},
    type=ActivityType.watching.value,
)

STALKS = [
    _prices_activity,
    _prices_activity,
    _prices_activity,
    _prices_activity,
    _prices_activity,
    Game("$help | Monopoly"),
    Game("$help | Adventure Capitalist"),
]

PAPAJ = [
    Activity(name="Barka", type=ActivityType.listening.value),
    Game(name="z Isabelle na kremówkach"),
    Game(name="okrutnik no po prostu"),
]

_hour = timedelta(hours=1)
_minute = timedelta(minutes=1)


def schedule_next_change(dt: datetime):
    next_change_t = dt.replace(second=5, minute=0) + _hour
    if dt.hour == 21 and dt.minute < 37:
        next_change_t = dt.replace(second=5, minute=37)
    elif dt.hour == 21 and dt.minute < 39:
        next_change_t = dt + _minute
    return (next_change_t - dt).seconds


def get_presence():
    dt = datetime.now()
    is_watching_stonks = (dt.isoweekday() == 7 and dt.hour in (5, 12)) or (
        dt.hour in (8, 12) and dt.isoweekday() != 7
    )
    if is_watching_stonks:
        activity = random.choice(STALKS)
    elif dt.hour == 21 and dt.minute == 37:
        activity = random.choice(PAPAJ)
    else:
        activity = random.choice(DEFAULT)

    return activity
