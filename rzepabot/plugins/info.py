# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from typing import Optional
from urllib.parse import quote

import pendulum
from discord import Embed, Emoji, File
from discord.ext import commands

from rzepabot.config import depoliszifaj, RZEPABOT_ROOT
from rzepabot.exceptions import RzepaException
from rzepabot.plugins.dodokod import Dodokod
from rzepabot.persistence import (
    PERSONALITIES,
    SPECIES,
    SPECIES_EMOJI,
    PERSONALITY_EMOJI,
    PERSONALITY_GENDER,
    REVERSE_SPECIES,
    Villager,
    db,
    Critter,
)

KNIFE_EMOJI = 690576498985271317

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

in_month = {
    1: "styczniu",
    2: "lutym",
    3: "marcu",
    4: "kwietniu",
    5: "maju",
    6: "czerwcu",
    7: "lipcu",
    8: "sierpniu",
    9: "wrześniu",
    10: "październiku",
    11: "listopadzie",
    12: "grudniu",
}


def villager_profile(title, villager: Villager):
    if villager.name == "Pietro":
        species = "🤡 Zwiastun apokalipsy"
    elif villager.name == "Hazel":
        species = "💩 ~~Żuk gnojak~~ Wiewiórka"
    else:
        species = f"{SPECIES_EMOJI[villager.species]} {villager.species}"
    embed = (
        Embed(
            color=0x8AD88A,
            title=title,
            url=f"https://animalcrossing.fandom.com/wiki/"
            f"{quote(villager.name)}",
            description=f'*"{villager.catchphrase}"*',
        )
        .set_thumbnail(url=villager.image_url)
        .add_field(
            name="Imię",
            value=f"{PERSONALITY_GENDER[villager.personality]} "
            f"{villager.name}",
            inline=False,
        )
        .add_field(name="Gatunek", value=f"{species}", inline=False,)
        .add_field(
            name="Osobowość",
            value=f"{PERSONALITY_EMOJI[villager.personality]} "
            f"{villager.personality}",
            inline=False,
        )
        .add_field(
            name="Urodziny",
            value=pendulum.now()
            .replace(month=villager.birthday_month, day=villager.birthday_day)
            .format("D MMMM"),
        )
    )
    return embed


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
                end = i
                start = end - 1
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

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["amiibomb"])
    async def amiibo(self, ctx: commands.Context):
        """
        Wyświetla instrukcje dotyczące nagrywania własnych kart amiibo.
        """
        return await ctx.send(
            embed=Embed(
                title="Poradnik jak nagrywać własne amiibo",
                description="Postępuj według instrukcji z [tego linku]("
                "https://www.reddit.com/r/Amiibomb/comments/5ywlol/"
                "howto_the_easy_guide_to_making_your_own_amiibo/).\n"
                "Zrzutki kart amiibo są dostępne za pomocą komendy "
                "`$zwierzaki karta <imię>`.",
                color=0x32CD32,
            ).set_image(
                url="https://animalcrossingworld.com/wp-content/uploads/"
                "2015/06/amiibo_card_AnimalCrossing_fan-790x309.png"
            )
        )

    @commands.group(aliases=["ryby", "r"])
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

    @ryby_.command(aliases=["miesiąc", "miesiac", "m"])
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

    @ryby_.command(aliases=["nowe", "n"])
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

    @ryby_.command(aliases=["koniec", "k"])
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

    @ryby_.command(aliases=["teraz", "t"])
    async def ryby_teraz(self, ctx: commands.Context):
        """
        Wypisuje dostępne w tej chwili do złowienia ryby.
        """
        for message in format_critters(
            "🎣 **Obecnie występujące ryby** 🎣\n\n",
            get_current_critters(is_fish=True),
        ):
            await ctx.send(message)

    @commands.group(aliases=["robaki", "insekty", "i"])
    async def insekty_(self, ctx: commands.Context):
        """
        Komendy dotyczące insektów. Wpisz `$help insekty`.

        Wywołane jako `$insekty styczeń` wypisuje informacje o robakach
        dostępnych w styczniu. Wywołane jako `$insekty` wypisuje informacje o
        robakach dostępnych w tej chwili.
        """
        if ctx.invoked_subcommand is None:
            if ctx.subcommand_passed:
                return await self.insekty_miesiac(
                    ctx, ctx.subcommand_passed.strip()
                )
            return await self.insekty_teraz(ctx)

    @insekty_.command(aliases=["miesiąc", "miesiac", "m"])
    async def insekty_miesiac(
        self, ctx: commands.Context, miesiac: Optional[str]
    ):
        """
        Wypisuje dostępne w danym (domyślnie obecnym) miesiącu insekty.
        """
        if not miesiac:
            now = pendulum.now()
            m_no = now.month - 1
            miesiac = rev_months[m_no]
        else:
            try:
                m_no = MONTHS[depoliszifaj(miesiac.lower())]
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawną nazwą miesiąca."
                )
        for message in format_critters(
            f"🎷🐛 **Insekty na miesiąc {miesiac.lower()}** 🎷🐛\n\n",
            get_critters_for_month(m_no, is_fish=False),
            print_time=True,
        ):
            await ctx.send(message)

    @insekty_.command(aliases=["nowe", "n"])
    async def insekty_nowe(
        self, ctx: commands.Context, miesiac: Optional[str]
    ):
        """
        Wypisuje nowe w danym (domyślnie obecnym) miesiącu insekty.
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
            f"🎷🐛 **Nowe insekty na miesiąc {miesiac.lower()}** 🎷🐛\n\n",
            get_new_critters_for_month(m_no, is_fish=False),
            print_time=True,
        ):
            await ctx.send(message)

    @insekty_.command(aliases=["koniec", "k"])
    async def insekty_koniec(
        self, ctx: commands.Context, miesiac: Optional[str]
    ):
        """
        Insekty dostępne tylko do końca danego (domyślnie obecnego) miesiąca.
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
            f"🎷🐛 **Insekty dostępne tylko do końca {mname}** 🎷🐛\n\n",
            get_leaving_critters_for_month(m_no, is_fish=False),
            print_time=True,
        ):
            await ctx.send(message)

    @insekty_.command(aliases=["teraz", "t"])
    async def insekty_teraz(self, ctx: commands.Context):
        """
        Wypisuje dostępne w tej chwili do złapania insekty.
        """
        for message in format_critters(
            "🎷🐛 **Obecnie występujące insekty** 🎷🐛\n\n",
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
                return await self.profile(
                    ctx, tekst=ctx.subcommand_passed.strip()
                )
            return await Dodokod.close(self, ctx)

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
            villagers = {}
            for villager in (
                Villager.select()
                .where(Villager.personality == personality)
                .order_by(Villager.species, Villager.name)
            ):
                villagers.setdefault(villager.species, []).append(
                    villager.name
                )
        embed = Embed(
            title=f':smiley_cat: Zwierzaki o osobowości _"{personality}"_ '
            f":smiley_cat:"
        )
        for p, vs in villagers.items():
            embed.add_field(
                name=p,
                value=", ".join(
                    f"[{n}](https://animalcrossing.fandom.com/wiki/"
                    f"{quote(n)})"
                    for n in vs
                ),
                inline=True,
            )
        return await ctx.send(PERSONALITY_EMOJI[personality], embed=embed)

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
        else:
            if tekst in REVERSE_SPECIES:
                species = REVERSE_SPECIES[tekst]
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
            villagers = {}
            for villager in (
                Villager.select()
                .where(Villager.species == species)
                .order_by(Villager.personality, Villager.name)
            ):
                villagers.setdefault(villager.personality, []).append(
                    villager.name
                )
        embed = Embed(
            title=f'{SPECIES_EMOJI[species]} Zwierzaki z gatunku _"{species}"_ '
            f"{SPECIES_EMOJI[species]}",
        )
        for p, vs in villagers.items():
            embed.add_field(
                name=p,
                value=", ".join(
                    f"[{n}](https://animalcrossing.fandom.com/wiki/"
                    f"{quote(n)})"
                    for n in vs
                ),
                inline=False,
            )
        return await ctx.send(embed=embed)

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
            emoji = SPECIES_EMOJI.get(villager.species, "")
            return await ctx.send(
                embed=villager_profile(
                    f"{emoji} **{villager.name}** {emoji}", villager
                )
            )

    @zwierzaki_.command(aliases=["profil", "p"])
    async def profile(self, ctx: commands.Context, *, tekst: str):
        """Wyświetla informacje o danym zwierzaku."""
        tekst = tekst.lower().strip()
        with db:
            villager = Villager.get_or_none(Villager.name ** tekst)
        if not villager:
            return await ctx.send(
                f":crying_cat_face: "
                f'Nie znaleziono zwierzaka o imieniu "{tekst.capitalize()}".'
            )
        emoji = SPECIES_EMOJI.get(villager.species, "")
        if villager.name == "Pietro":
            knife = self.bot.get_emoji(KNIFE_EMOJI)
            knife: Emoji
            if knife and knife.is_usable():
                return await ctx.send(
                    embed=villager_profile(
                        f"{knife} **{villager.name}** {knife}", villager
                    ),
                )
        return await ctx.send(
            embed=villager_profile(
                f"{emoji} **{villager.name}** {emoji}", villager
            ),
        )

    @zwierzaki_.command(aliases=["karta", "k"])
    async def card(self, ctx: commands.Context, *, tekst: str):
        """Wyświetla informacje o danym zwierzaku, plus prezent."""
        tekst = tekst.lower().strip()
        with db:
            villager = Villager.get_or_none(Villager.name ** tekst)
        if not villager:
            return await ctx.send(
                f":crying_cat_face: "
                f'Nie znaleziono zwierzaka o imieniu "{tekst.capitalize()}".'
            )
        emoji = SPECIES_EMOJI.get(villager.species, "")
        if villager.name == "Pietro":
            knife = self.bot.get_emoji(KNIFE_EMOJI)
            knife: Emoji
            if knife and knife.is_usable():
                return await ctx.send(
                    embed=villager_profile(
                        f"{knife} **{villager.name}** {knife}", villager
                    ),
                )
        extra_args = {}
        path = (
            RZEPABOT_ROOT
            / "rzepabot"
            / "data"
            / "cards"
            / f"{villager.name}.bin"
        )
        if path.is_file():
            extra_args["file"] = File(path.absolute())
        return await ctx.send(
            embed=villager_profile(
                f"{emoji} **{villager.name}** {emoji}", villager
            ),
            **extra_args,
        )

    @zwierzaki_.command(aliases=["urodziny", "u"])
    async def birthday(
        self,
        ctx: commands.Context,
        miesiac: Optional[int],
        dzien: Optional[int],
    ):
        """
        Wyświetla zwierzaki według urodzin.

        Wywołane jako `$zwierzaki urodziny` wyświetla zwierzaki obchodzące
        urodziny dzisiaj.
        Wywołane jako `$zwierzaki urodziny 12` wyświetla zwierzaki
        obchodzące urodziny w grudniu.
        Wywołane jako `$zwierzaki urodziny 12 24` wyświetla zwierzaki
        obchodzące urodziny 24go grudnia.
        """
        now = pendulum.now()
        if miesiac is None and dzien is None:
            miesiac = now.month
            dzien = now.day
        if dzien is None:
            try:
                human_date = f"w {in_month[miesiac]}"
            except KeyError:
                raise RzepaException(
                    f"{miesiac} nie jest poprawnym numerem miesiąca."
                )
        else:
            human_date = now.replace(month=miesiac, day=dzien).format("D MMMM")

        with db:
            filters = [Villager.birthday_month == miesiac]
            if dzien is not None:
                filters.append(Villager.birthday_day == dzien)
            villagers = list(
                Villager.select()
                .where(*filters)
                .order_by(Villager.birthday_month, Villager.birthday_day)
                .objects()
            )
        if not villagers:
            return await ctx.send(
                f":calendar: "
                f"Żaden zwierzak nie obchodzi urodzin {human_date}."
            )
        elif len(villagers) == 1:
            v = villagers[0]
            emoji = SPECIES_EMOJI.get(v.species, "")
            return await ctx.send(
                f":calendar: "
                f"{human_date.capitalize()} urodziny obchodzi {v.name}.",
                embed=villager_profile(f"{emoji} **{v.name}** {emoji}", v),
            )
        else:
            embed = Embed(
                title=f":calendar: Zwierzaki obchodzące urodziny"
                f" {human_date} :calendar:",
                color=0x8AD88A,
            )
            vdays = {}
            for v in villagers:
                vdays.setdefault(v.birthday_day, []).append(v)
            for day, vs in vdays.items():
                v = ", ".join(
                    [
                        f"[{v.name}](https://animalcrossing.fandom.com/wiki/"
                        f"{quote(v.name)})"
                        for v in vs
                    ]
                )
                embed.add_field(
                    name=now.replace(month=miesiac, day=day).format("D MMMM"),
                    value=v,
                )
            return await ctx.send(embed=embed)
