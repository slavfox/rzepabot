# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from typing import Optional
from discord import Member, Embed
from discord.ext import commands
from peewee import JOIN, IntegrityError
from pendulum import instance, timezone
from discord.ext.commands.converter import MemberConverter
from rzepabot.plugins.info import villager_profile

from rzepabot.exceptions import RzepaException
from rzepabot.persistence import (
    DodoCode,
    Island,
    User,
    db,
    get_user_and_guild,
    Residency,
    Villager,
    FRUIT,
)


def match_fc(friend_code: str) -> str:
    fc = friend_code.upper()
    if fc.startswith("SW"):
        fc = fc[2:]
    fc = fc.replace("-", "").replace(" ", "")
    if not fc.isnumeric() or not len(fc) == 12:
        raise RzepaException(f"{friend_code} nie jest poprawnym Friend Code.")
    return fc


def format_fc(friend_code: str) -> str:
    return f"SW-{friend_code[:4]}-{friend_code[4:8]}-{friend_code[8:]}"


def format_profile(island: Island, user: Member) -> Embed:
    if (
        role := getattr(user, "top_role", None)
    ) and role.colour.value != 0xFFFFFF:
        colour = role.colour
    else:
        colour = 0x8AD88A
    avatar_url = f"{user.avatar_url.BASE}{user.avatar_url._url}"
    title = island.island_name or f"Wyspa użytkownika {user.display_name}"
    embed = Embed(colour=colour, title=title).set_thumbnail(url=avatar_url)
    if island.island_name:
        embed.add_field(
            name="Nazwa wyspy", value=island.island_name, inline=False
        )
    if island.character_name:
        embed.add_field(
            name="Imię postaci", value=island.character_name, inline=False
        )

    with db:
        villagers = (
            Villager.select(Villager.name)
            .join(Residency)
            .where(Residency.acprofile == island)
            .order_by(Villager.name)
            .tuples()
        )
        residents = [
            f"[{name}](https://animalcrossing.fandom.com/wiki/{name})"
            for name, in villagers
        ]
    if residents:
        embed.add_field(
            name="Mieszkańcy", value=", ".join(residents), inline=False
        )
    if island.native_fruit:
        fruit = FRUIT[island.native_fruit]
        embed.add_field(
            name="Natywny owoc",
            value=f"{fruit.emoji} " f"{fruit.name.capitalize()}",
            inline=False,
        )
    if island.friend_code:
        embed.add_field(
            name="Friend Code",
            value=f"`{format_fc(island.friend_code)}`",
            inline=False,
        )
    return embed


class Profil(commands.Cog):
    """Komendy dotyczące informacji o użytkownikach."""

    @commands.command(aliases=["fc", "friendcode"])
    async def set_fc(self, ctx: commands.Context, friend_code: str):
        """
        Pozwala ustawić swój Friend Code.
        """
        fc = match_fc(friend_code)
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild.id, db)
            island, _ = Island.get_or_create(villager=user)
            island.friend_code = fc
            island.save()
        return await ctx.send(
            f"🤝 {ctx.author.mention}, zarejestrowano twój "
            f"kod `{format_fc(fc)}`."
        )

    @commands.command(aliases=["wyspa"])
    async def set_island_name(
        self, ctx: commands.Context, *, nazwa: Optional[str]
    ):
        """
        Pozwala ustawić nazwę swojej wyspy.
        """
        if nazwa:
            nazwa = await commands.clean_content().convert(ctx, nazwa)
            nazwa = nazwa.strip()
            if not nazwa:
                nazwa = None
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild.id, db)
            island = Island.get_or_none(Island.villager == user)
            if not island:
                if not nazwa:
                    return await ctx.send(
                        f"🗿️ {ctx.author.mention}, nie masz profilu, "
                        f"więc nie można wyczyścić nazwy twojej wyspy."
                    )
                island = Island(villager=user)
            island.island_name = nazwa
            island.save()
        if not nazwa:
            return await ctx.send(
                f"🏝️ {ctx.author.mention}, wyczyszczono nazwę twojej wyspy."
            )
        return await ctx.send(
            f"🏝️ {ctx.author.mention}, ustawiono nazwę twojej wyspy na"
            f"`{nazwa}`."
        )

    @commands.command(aliases=["postać", "postac"])
    async def set_character_name(
        self, ctx: commands.Context, *, nazwa: Optional[str]
    ):
        """
        Pozwala ustawić imię swojej postaci.
        """
        if nazwa:
            nazwa = await commands.clean_content().convert(ctx, nazwa)
            nazwa = nazwa.strip()
            if not nazwa:
                nazwa = None
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild.id, db)
            island = Island.get_or_none(Island.villager == user)
            if not island:
                if not nazwa:
                    return await ctx.send(
                        f"🗿️ {ctx.author.mention}, nie masz profilu, "
                        f"więc nie można wyczyścić imienia twojej postaci."
                    )
                island = Island(villager=user)
            island.character_name = nazwa
            island.save()
        if not nazwa:
            return await ctx.send(
                f"🧒 {ctx.author.mention}, wyczyszczono imię twojej postaci."
            )
        return await ctx.send(
            f"️🧒 {ctx.author.mention}, ustawiono imię twojej postaci na"
            f"`{nazwa}`."
        )

    @commands.command(aliases=["wprowadź", "wprowadz"])
    async def move_in(self, ctx: commands.Context, zwierzak: str):
        """
        Dodaje mieszkańca do Twojej wyspy.
        """
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild.id, db)
            island, created = Island.get_or_create(villager=user)
            if not created:
                if (
                    Residency.select()
                    .where(Residency.acprofile == island)
                    .count()
                    >= 10
                ):
                    raise RzepaException(
                        f"{ctx.author.mention}, "
                        f"masz już 10 zwierzaków na swojej wyspie. Zanim "
                        f"wprowadzisz nowego, musisz kogoś wyprowadzić."
                    )

            villager = (
                Villager.select().where(Villager.name ** zwierzak).first()
            )
            if not villager:
                clean = await commands.clean_content().convert(ctx, zwierzak)
                raise RzepaException(f"Nie ma takiego zwierzaka: {clean}")
            try:
                Residency.create(villager=villager, acprofile=island)
            except IntegrityError:
                raise RzepaException(
                    f"{villager.name} jest już na twojej " f"wyspie."
                )
        return await ctx.send(
            f"🏕 {ctx.author.mention}, zarejestrowano nowego mieszkańca "
            f"twojej wyspy: {villager.name}.",
            embed=villager_profile(villager),
        )

    @commands.command(aliases=["wyprowadź", "wyprowadz", "wyrzuć", "wyrzuc"])
    async def move_out(self, ctx: commands.Context, zwierzak: str):
        """
        Wyrzuca mieszkańca z Twojej wyspy.
        """
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild.id, db)
            island, created = Island.get_or_create(villager=user)
            residency = (
                Residency.select(Residency, Villager)
                .where(
                    Residency.acprofile == island, Villager.name ** zwierzak
                )
                .first()
            )
            if not residency:
                clean = await commands.clean_content().convert(ctx, zwierzak)
                raise RzepaException(
                    f"{ctx.author.mention}, na twojej wyspie "
                    f"nie ma zwierzaka: {clean}"
                )
            residency.delete_instance()
        return await ctx.send(
            f"🏕 {ctx.author.mention}, usunięto z twojej wyspy zwierzaka: "
            f"{residency.villager.name}.",
            embed=villager_profile(residency.villager),
        )

    @commands.command(aliases=["profil"])
    async def show_profile(
        self, ctx: commands.Context, user: Optional[Member]
    ):
        """
        Wyświetla profil danego użytkownika (domyślnie własny).
        """
        if user is None:
            user = ctx.author
        with db:
            island = (
                Island.select()
                .join(User)
                .where(User.discord_id == user.id)
                .first()
            )
        if not island:
            raise RzepaException(
                f"Użytkownik {user.display_name} nie ma profilu."
            )
        embed = format_profile(island, user)
        return await ctx.send(
            f"️🏝 **Profil użytkownika {user.display_name}** 🏝", embed=embed
        )
