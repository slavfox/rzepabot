# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from rzepabot.config import tznow_dt
from rzepabot.persistence import StalkPrice, User, db

if TYPE_CHECKING:
    from matplotlib.pyplot import Axes
    from typing import Sequence


def datetime_from_timestamp(ts):
    return datetime(
        year=ts.year,
        month=ts.month,
        day=ts.day,
        hour=ts.hour,
        minute=ts.minute,
    )


def get_current_week_prices(user: User):
    now = tznow_dt()
    start_of_week = (
        now.shift(weekday=6).shift(weeks=-1).replace(hour=7, minute=0)
    )
    with db:
        prices = (
            StalkPrice.select(StalkPrice.timestamp, StalkPrice.price)
            .where(
                StalkPrice.user == User,
                StalkPrice.timestamp > start_of_week,
                StalkPrice.is_buy_price == False,
            )
            .order_by(StalkPrice.timestamp)
        )
        buyprice = (
            StalkPrice.select(StalkPrice.price)
            .where(
                StalkPrice.user == User,
                StalkPrice.timestamp > start_of_week,
                StalkPrice.is_buy_price == True,
            )
            .order_by(StalkPrice.timestamp.desc())
            .get_or_none()
        )
        if buyprice is not None:
            buyprice = buyprice.price
    return prices, buyprice


def process_prices(prices):
    pricelist = []
    datelist = []
    for price in prices:
        pricelist.append(price.price)
        if price.timestamp.hour >= 12:
            datelist.append(price.timestamp.replace(hour=18))
        else:
            datelist.append(price.timestamp.replace(hour=6))
    return datelist, pricelist


def draw_plot(prices, buyprice=None):
    datelist, pricelist = prices
    with plt.xkcd():
        fig, ax = plt.subplots()
        ax: Axes
        ax.plot(
            datelist, pricelist, "o-", label="Cena sprzedaży u Nooklingów",
        )
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_minor_locator(mdates.HourLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))

        if buyprice:
            ax.plot(
                datelist,
                [buyprice for _ in datelist],
                label="Cena kupna u Daisy",
            )

        for i, p in enumerate(pricelist):
            ax.annotate(
                p, (datelist[i], p), (0, 10), textcoords="offset " "pixels"
            )

        ax.set_ylabel("Dzwoneczki")
        fig.autofmt_xdate()
        ax.grid(axis="y")
        fig.tight_layout()
        return fig, ax


def fit_small_spike(sell_prices: Sequence[StalkPrice], buy_price=None):
    likelihood = 0

    if buy_price is None:
        buy_price_range = 0.4 * 90, 0.9 * 110
    else:
        buy_price_range = buy_price, buy_price

    # Match initial base rate
    guess_monday_session1_price  # TODO
    dt = datetime_from_timestamp(sell_prices[0].timestamp)
    if dt.weekday() == 0:
        if dt.hour < 12:
            monday_session1_price_range = (
                sell_prices[0].price,
                sell_prices[0].price,
            )
        else:
            monday_session1_price_range = ...


def guess_pattern(buy_price=None, sell_prices=()):
    ...


if __name__ == "__main__":
    from collections import namedtuple
    from datetime import timedelta

    monday = datetime(year=2020, month=3, day=30, hour=8)
    prices = []
    lastdate = monday
    StalkPrice = namedtuple("StalkPrice", ["price", "timestamp"])
    for i, price in enumerate(
        [74, 70, 67, 63, 59, 56, 51, 132, 105, 152, 187]
    ):
        prices.append(StalkPrice(price, lastdate))
        lastdate = lastdate + (
            timedelta(hours=20) if i % 2 else timedelta(hours=4)
        )
    del prices[3:4]
    del prices[6:8]
    fig, ax = draw_plot(process_prices(prices), 94)
    fig.savefig("plot.png")
