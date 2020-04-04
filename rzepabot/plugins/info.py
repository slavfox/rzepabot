# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from typing import Optional

import pendulum
from discord import Embed
from discord.ext import commands

from rzepabot.config import depoliszifaj
from rzepabot.exceptions import RzepaException
from rzepabot.persistence import (
    PERSONALITIES,
    SPECIES,
    SPECIES_EMOJI,
    Villager,
    db,
    Critter,
)

MONTHS = {
    "styczen": 0,
    "luty": 1,
    "marzec": 2,
    "kwiecien": 3,
    "maj": 4,
    "czerwiec": 5,
    "lipiec": 6,
    "sierpien": 7,
    "wrzesien": 8,
    "pazdziernik": 9,
    "listopad": 10,
    "grudzien": 11,
}
rev_months = {
    0: "styczeń",
    1: "luty",
    2: "marzec",
    3: "kwiecień",
    4: "maj",
    5: "czerwiec",
    6: "lipiec",
    7: "sierpień",
    8: "wrzesień",
    9: "październik",
    10: "listopad",
    11: "grudzień",
}


def villager_profile(villager: Villager):
    return (
        Embed(
            color=0x8AD88A,
            title=f"{villager.name}",
            url=f"https://animalcrossing.fandom.com/wiki/{villager.name}",
            description=f'*"{villager.catchphrase}"*',
        )
        .set_thumbnail(url=villager.image_url)
        .add_field(name="Imię", value=villager.name, inline=False)
        .add_field(name="Gatunek", value=villager.species, inline=False)
        .add_field(name="Osobowość", value=villager.personality, inline=False)
        .add_field(
            name="Urodziny",
            value=pendulum.now()
            .replace(month=villager.birthday_month, day=villager.birthday_day)
            .format("D MMMM"),
        )
    )


def month_mask_to_printable(mask):
    ranges = []
    if mask == 0b111111111111:
        return "cały rok"
    start = (mask & 1) - 1
    end = start
    for i in range(1, 12):
        if mask & (1 << i):
            if start == -1:
                start = end = i
            elif (i - end) == 1:
                end = i
            else:
                ranges.append((start + 1, end + 1))
                start = -1
                end = -1
    if start != -1:
        ranges.append((start + 1, end + 1))
    if ranges[0][0] == 1 and ranges[-1][1] == 12:
        ranges[0] = (ranges[-1][0], ranges[0][1])
        ranges.pop()
    now = pendulum.now()
    printable_ranges = [
        now.replace(month=r[0]).format("MMM")
        + "-"
        + now.replace(month=r[1]).format("MMM")
        for r in ranges
    ]
    return ", ".join(printable_ranges)


def hour_mask_to_printable(mask):
    ranges = []
    if mask == 0b111111111111111111111111:
        return "cały dzień"
    start = (mask & 1) - 1
    end = start
    for i in range(1, 24):
        if mask & (1 << i):
            if start == -1:
                start = end = i
            elif (i - end) == 1:
                end = i
            else:
                ranges.append((start, end))
                start = -1
                end = -1
    if start != -1:
        ranges.append((start, end))
    if ranges[0][0] == 0 and ranges[-1][1] == 23:
        ranges[0] = (ranges[-1][0], ranges[0][1])
        ranges.pop()
    printable_ranges = [f"{r[0]}:00-{(r[1] + 1) % 24}:00" for r in ranges]
    return ", ".join(printable_ranges)


def get_current_critters(
    is_fish=True, include_time=False, order_by=Critter.price.desc()
):
    now = pendulum.now()
    critters = []

    now_month = 2 ** (now.month - 1)
    now_time = 2 ** now.hour
    with db:
        for critter in (
            Critter.select()
            .where(
                Critter.is_fish == is_fish,
                Critter.month_mask.bin_and(now_month) > 0,
                Critter.time_mask.bin_and(now_time) > 0,
            )
            .order_by(order_by)
        ):
            c = [critter.name, critter.price, critter.location]
            if include_time:
                c += [
                    hour_mask_to_printable(critter.time_mask),
                    month_mask_to_printable(critter.month_mask),
                ]
            critters.append(c)
    return critters


def get_critters_for_month(
    month, is_fish=True, include_time=True, order_by=Critter.price.desc()
):
    critters = []
    with db:
        for critter in (
            Critter.select()
            .where(
                Critter.is_fish == is_fish,
                Critter.month_mask.bin_and(2 ** month) > 0,
            )
            .order_by(order_by)
        ):
            c = [critter.name, critter.price, critter.location]
            if include_time:
                c += [
                    hour_mask_to_printable(critter.time_mask),
                    month_mask_to_printable(critter.month_mask),
                ]
            critters.append(c)
    return critters


def get_leaving_critters_for_month(
    month, is_fish=True, include_time=True, order_by=Critter.price.desc()
):
    critters = []
    if month == 11:
        next_mask = 1
    else:
        next_mask = 2 ** (month + 1)
    month_mask = 2 ** month
    with db:
        for critter in (
            Critter.select()
            .where(
                Critter.is_fish == is_fish,
                Critter.month_mask.bin_and(month_mask | next_mask)
                == month_mask,
            )
            .order_by(order_by)
        ):
            c = [critter.name, critter.price, critter.location]
            if include_time:
                c += [
                    hour_mask_to_printable(critter.time_mask),
                    month_mask_to_printable(critter.month_mask),
                ]
            critters.append(c)
    return critters


def get_new_critters_for_month(
    month, is_fish=True, include_time=True, order_by=Critter.price.desc()
):
    critters = []
    if month == 0:
        previous_mask = 11
    else:
        previous_mask = 2 ** (month - 1)
    month_mask = 2 ** month
    with db:
        for critter in (
            Critter.select()
            .where(
                Critter.is_fish == is_fish,
                Critter.month_mask.bin_and(month_mask | previous_mask)
                == month_mask,
            )
            .order_by(order_by)
        ):
            c = [critter.name, critter.price, critter.location]
            if include_time:
                c += [
                    hour_mask_to_printable(critter.time_mask),
                    month_mask_to_printable(critter.month_mask),
                ]
            critters.append(c)
    return critters


def format_critters(heading, critters, print_time=False):
    s = heading
    messages = []
    for c in critters:
        line = f"**{c[0]}**: ₿{c[1]}, {c[2].lower()}"
        if print_time:
            line += f", {c[3]}, {c[4]}"
        line += "\n"
        if len(s + line) > 1998:
            messages.append(s)
            s = ""
        s += line
    messages.append(s)
    return messages


class Info(commands.Cog):
    """
    Komendy do szukania informacji na temat Animal Crossing: New Horizons.
    """

    @commands.group(aliases=["ryby"])
    async def ryby_(self, ctx: commands.Context):
        """
        Komendy dotyczące ryb. Wpisz `$help ryby`.

        Wywołane jako `$ryby styczeń` wypisuje informacje o rybach
        dostępnych w styczniu. Wywołane jako `$ryby` wypisuje informacje o
        rybach dostępnych w tej chwili.
        """
        if ctx.invoked_subcommand is None:
            if ctx.subcommand_passed:
                return await self.ryby_miesiac(
                    ctx, ctx.subcommand_passed.strip()
                )
            return await self.ryby_teraz(ctx)

    @ryby_.command(aliases=["miesiąc", "miesiac"])
    async def ryby_miesiac(
        self, ctx: commands.Context, miesiac: Optional[str]
    ):
        """
        Wypisuje dostępne w danym (domyślnie obecnym) miesiącu ryby.
        """
        if not miesiac:
            m_no = pendulum.now().month - 1
            miesiac = rev_months[m_no]
        else:
            try:
                m_no = MONTHS[depoliszifaj(miesiac.lower())]
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawną nazwą " f"miesiąca."
                )
        for message in format_critters(
            f"🎣 **Ryby na miesiąc {miesiac.lower()}** 🎣\n\n",
            get_critters_for_month(m_no, is_fish=True),
            print_time=True,
        ):
            await ctx.send(message)

    @ryby_.command(aliases=["nowe"])
    async def ryby_nowe(self, ctx: commands.Context, miesiac: Optional[str]):
        """
        Wypisuje nowe w danym (domyślnie obecnym) miesiącu ryby.
        """
        if not miesiac:
            m_no = pendulum.now().month - 1
            miesiac = rev_months[m_no]
        else:
            try:
                m_no = MONTHS[depoliszifaj(miesiac.lower())]
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawną nazwą miesiąca."
                )
        for message in format_critters(
            f"🎣 **Nowe ryby na miesiąc {miesiac.lower()}** 🎣\n\n",
            get_new_critters_for_month(m_no, is_fish=True),
            print_time=True,
        ):
            await ctx.send(message)

    @ryby_.command(aliases=["koniec"])
    async def ryby_koniec(self, ctx: commands.Context, miesiac: Optional[str]):
        """
        Ryby dostępne tylko do końca danego (domyślnie obecnego) miesiąca.
        """
        if not miesiac:
            m_no = pendulum.now().month - 1
        else:
            try:
                m_no = MONTHS[depoliszifaj(miesiac.lower())]
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawną nazwą miesiąca."
                )
        mname = pendulum.now().replace(month=m_no + 1).format("MMMM")
        for message in format_critters(
            f"🎣 **Ryby dostępne tylko do końca {mname}** 🎣\n\n",
            get_leaving_critters_for_month(m_no, is_fish=True),
            print_time=True,
        ):
            await ctx.send(message)

    @ryby_.command(aliases=["teraz"])
    async def ryby_teraz(self, ctx: commands.Context):
        """
        Wypisuje dostępne w tej chwili do złowienia ryby.
        """
        for message in format_critters(
            "🎣 **Obecnie występujące ryby** 🎣\n\n",
            get_current_critters(is_fish=True),
        ):
            await ctx.send(message)

    @commands.group(aliases=["robaki"])
    async def robaki_(self, ctx: commands.Context):
        """
        Komendy dotyczące robaków. Wpisz `$help robaki`.

        Wywołane jako `$robaki styczeń` wypisuje informacje o robakach
        dostępnych w styczniu. Wywołane jako `$robaki` wypisuje informacje o
        robakach dostępnych w tej chwili.
        """
        if ctx.invoked_subcommand is None:
            if ctx.subcommand_passed:
                return await self.robaki_miesiac(
                    ctx, ctx.subcommand_passed.strip()
                )
            return await self.robaki_teraz(ctx)

    @robaki_.command(aliases=["miesiąc", "miesiac"])
    async def robaki_miesiac(
        self, ctx: commands.Context, miesiac: Optional[str]
    ):
        """
        Wypisuje dostępne w danym (domyślnie obecnym) miesiącu robaki.
        """
        if not miesiac:
            m_no = pendulum.now().month - 1
        else:
            try:
                m_no = MONTHS[depoliszifaj(miesiac.lower())]
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawną nazwą miesiąca."
                )
        for message in format_critters(
            f"🎷🐛 **Robaki na miesiąc {miesiac.lower()}** 🎷🐛\n\n",
            get_critters_for_month(m_no, is_fish=False),
            print_time=True,
        ):
            await ctx.send(message)

    @robaki_.command(aliases=["nowe"])
    async def robaki_nowe(self, ctx: commands.Context, miesiac: Optional[str]):
        """
        Wypisuje nowe w danym (domyślnie obecnym) miesiącu robaki.
        """
        if not miesiac:
            m_no = pendulum.now().month - 1
            miesiac = rev_months[m_no]
        else:
            try:
                m_no = MONTHS[depoliszifaj(miesiac.lower())]
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawną nazwą miesiąca."
                )
        for message in format_critters(
            f"🎷🐛 **Nowe robaki na miesiąc {miesiac.lower()}** 🎷🐛\n\n",
            get_new_critters_for_month(m_no, is_fish=False),
            print_time=True,
        ):
            await ctx.send(message)

    @robaki_.command(aliases=["koniec"])
    async def robaki_koniec(
        self, ctx: commands.Context, miesiac: Optional[str]
    ):
        """
        Robaki dostępne tylko do końca danego (domyślnie obecnego) miesiąca.
        """
        if not miesiac:
            m_no = pendulum.now().month - 1
        else:
            try:
                m_no = MONTHS[depoliszifaj(miesiac.lower())]
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawną nazwą miesiąca."
                )
        mname = pendulum.now().replace(month=m_no + 1).format("MMMM")
        for message in format_critters(
            f"🎷🐛 **Robaki dostępne tylko do końca {mname}** 🎷🐛\n\n",
            get_leaving_critters_for_month(m_no, is_fish=False),
            print_time=True,
        ):
            await ctx.send(message)

    @robaki_.command(aliases=["teraz"])
    async def robaki_teraz(self, ctx: commands.Context):
        """
        Wypisuje dostępne w tej chwili do złapania robaki.
        """
        for message in format_critters(
            "🎷🐛 **Obecnie występujące robaki** 🎷🐛\n\n",
            get_current_critters(is_fish=False),
        ):
            await ctx.send(message)

    @commands.group(aliases=["zwierzaki", "zwierzak", "zwierz", "z"])
    async def zwierzaki_(self, ctx: commands.Context):
        """
        Komend dotyczące zwierzaków. Wpisz `$help zwierzaki`.

        Bez subkomendy wyświetla informacje o zwierzaku o podanym imieniu.
        """
        if ctx.invoked_subcommand is None:
            if ctx.subcommand_passed:
                return await self.profile(ctx, ctx.subcommand_passed.strip())
            commands = sorted(
                {
                    f"`{command.aliases[0]}`"
                    for command in self.zwierzaki_.walk_commands()
                }
            )
            raise RzepaException(
                f"Musisz podać jedną z komend: "
                f"{', '.join(commands[:-1])}, lub {commands[-1]}"
            )

    @zwierzaki_.command(aliases=["osobowość", "o"])
    async def personality(self, ctx: commands.Context, tekst: str):
        """
        Znajduje zwierzaki o danej osobowości.

        Przyjmuje również angielskie nazwy.
        """
        tekst = tekst.lower().strip()
        personality = None
        for aliases in PERSONALITIES:
            if tekst in aliases:
                personality = aliases[0].capitalize()
                break
        if not personality:
            options = [f"`{alias[0]}`" for alias in PERSONALITIES]
            raise RzepaException(
                f"{tekst} nie jest osobowością zwierzaków w New "
                f"Horizons. Podaj jedną z: {', '.join(options[:-1])}, lub"
                f"{options[-1]}."
            )
        with db:
            villagers = []
            for villager in (
                Villager.select()
                .where(Villager.personality == personality)
                .order_by(Villager.name)
            ):
                villagers.append(villager.name)

        return await ctx.send(
            f":smiley_cat: "
            f'**Zwierzaki o osobowości _"{personality}"_** :smiley_cat:\n\n'
            f"{', '.join(villagers)}"
        )

    @zwierzaki_.command(aliases=["gatunek", "g"])
    async def species(self, ctx: commands.Context, tekst: str):
        """
        Znajduje zwierzaki z danego gatunku.

        Przyjmuje również angielskie nazwy.
        """
        tekst = tekst.lower().strip()
        species = None
        for aliases in SPECIES:
            if tekst in aliases:
                species = aliases[0].capitalize()
                break
        if not species:
            options = [
                f"`{a[0]}`"
                if a == "Orzeł" or not a[0].endswith("eł")
                else f"`{a[0][:-2]}`"
                for a in SPECIES
            ]
            raise RzepaException(
                f"`{tekst}` nie jest gatunkiem zwierzaków które mogą "
                f"zamieszkać na wyspie w New Horizons. "
                f"Podaj jedną z: {', '.join(options[:-1])}, "
                f"lub"
                f"{options[-1]}."
            )
        with db:
            villagers = []
            for villager in (
                Villager.select()
                .where(Villager.species == species)
                .order_by(Villager.name)
            ):
                villagers.append(villager.name)

        return await ctx.send(
            f":smiley_cat: "
            f'**Zwierzaki z gatunku _"{species}"_** :smiley_cat:\n\n'
            f"{', '.join(villagers)}"
        )

    @zwierzaki_.command(aliases=["szukaj", "znajdź", "s", "z"])
    async def find(self, ctx: commands.Context, tekst: str):
        """Znajduje zwierzaki których imię zawiera podany tekst."""
        tekst = tekst.lower().strip()
        with db:
            villagers = []
            for villager in Villager.select().where(
                Villager.name ** f"%{tekst}%"
            ):
                villagers.append(villager.name)
        if not villagers:
            return await ctx.send(
                f":crying_cat_face: "
                f'Nie znaleziono zwierzaków których imię zawiera "{tekst}".'
            )
        if len(villagers) > 1:
            return await ctx.send(
                f":smiley_cat: "
                f'**Zwierzaki których imię zawiera _"{tekst}"_** '
                f":smiley_cat:\n\n"
                f"{', '.join(villagers)}"
            )
        else:
            return await ctx.send(embed=villager_profile(villager))

    @zwierzaki_.command(aliases=["profil", "p"])
    async def profile(self, ctx: commands.Context, tekst: str):
        """Wyświetla informacje o danym zwierzaku."""
        tekst = tekst.lower().strip()
        with db:
            villager = Villager.get_or_none(Villager.name ** tekst)
        if not villager:
            return await ctx.send(
                f":crying_cat_face: "
                f'Nie znaleziono zwierzaka o imieniu "{tekst.capitalize()}".'
            )
        emoji = SPECIES_EMOJI.get(villager.species)
        return await ctx.send(
            f"{emoji} **{villager.name}** {emoji}",
            embed=villager_profile(villager),
        )
