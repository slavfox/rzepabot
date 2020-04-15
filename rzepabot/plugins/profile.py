# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from typing import Optional
from discord import Member, Embed, Guild as DiscordGuild
from discord.ext import commands
from peewee import JOIN, IntegrityError
from pendulum import instance, timezone, now
from discord.ext.commands.converter import MemberConverter
from rzepabot.plugins.info import villager_profile
from urllib.parse import quote, urlencode

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
    HotItem,
    Guild,
    GuildMembership,
    tznow_dt,
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


def format_profile(
    island: Island, user: Member, dodocode: str = None, item: str = None
) -> Embed:
    if (
        role := getattr(user, "top_role", None)
    ) and role.colour.value != 0xFFFFFF:
        colour = role.colour
    else:
        colour = 0x8AD88A
    avatar_url = f"{user.avatar_url.BASE}{user.avatar_url._url}"
    title = island.island_name or f"Wyspa użytkownika {user.display_name}"
    embed = Embed(colour=colour, title=title).set_thumbnail(url=avatar_url)
    if item:
        embed.add_field(
            name="📦 **Gorący przedmiot na dziś** 📦",
            value=f"[{item}]("
            f"https://animalcrossing.fandom.com/wiki/Special:Search?"
            f"{urlencode({'query': item})})",
            inline=False,
        )
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
            f"[{n}](https://animalcrossing.fandom.com/wiki/{quote(n)})"
            for n, in villagers
        ]
    if residents:
        embed.add_field(
            name=f"Mieszkańcy ({len(residents)}/10)",
            value=", ".join(residents),
            inline=False,
        )
    if island.native_fruit:
        fruit = FRUIT[island.native_fruit]
        embed.add_field(
            name="Natywny owoc",
            value=f"{fruit.emoji} " f"{fruit.pl_name.capitalize()}",
            inline=False,
        )
    if island.friend_code:
        embed.add_field(
            name="Friend Code",
            value=f"`{format_fc(island.friend_code)}`",
            inline=False,
        )
    if dodocode:
        embed.description = (
            f"🗺 **Ta wyspa jest obecnie otwarta!** 🗺\n"
            f"Możesz odwiedzić ją z dodokodem `{dodocode}`."
        )

    return embed


class Profil(commands.Cog):
    """Komendy dotyczące informacji o użytkownikach."""

    @commands.command(aliases=["owoc"])
    async def set_fruit(self, ctx: commands.Context, owoc: str):
        """
        Pozwala ustawić natywny owoc wyspy.
        """
        owoc = owoc.strip().lower()
        fruit_index = None
        _fruit = None
        for idx, f in FRUIT.items():
            if owoc in [f.name, f.pl_name, f.emoji, *f.aliases]:
                fruit_index = idx
                _fruit = f
                break
        if fruit_index is None:
            owoc = await commands.clean_content().convert(ctx, owoc)
            raise RzepaException(
                f"{owoc} nie jest możliwym natywnym owocem wyspy."
            )
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
            island, _ = Island.get_or_create(villager=user)
            island.native_fruit = fruit_index
            island.save()
        return await ctx.send(
            f"{_fruit.emoji} {ctx.author.mention}, zarejestrowano "
            f"**{_fruit.pl_name}** jako natywny owoc twojej wyspy."
        )

    @commands.command(aliases=["fc", "friendcode"])
    async def set_fc(self, ctx: commands.Context, friend_code: str):
        """
        Pozwala ustawić swój Friend Code.
        """
        fc = match_fc(friend_code)
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
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
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
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
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
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
    async def move_in(self, ctx: commands.Context, *, zwierzaki: str):
        """
        Dodaje 1 lub więcej mieszkańców (rozdzielonych przecinkami) na wyspę.
        """
        villagers = [z.strip() for z in zwierzaki.split(",")]
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
            island, created = Island.get_or_create(villager=user)
            if not created:
                if Residency.select().where(
                    Residency.acprofile == island
                ).count() > 10 - len(villagers):
                    raise RzepaException(
                        f"{ctx.author.mention}, "
                        f"na wyspie możesz mieć maksymalnie 10 zwierzaków."
                    )
            valid_villagers = []
            with db.atomic() as transaction:
                for v in villagers:
                    villager = (
                        Villager.select().where(Villager.name ** v).first()
                    )
                    if not villager:
                        clean = await commands.clean_content().convert(ctx, v)
                        transaction.rollback()
                        raise RzepaException(
                            f"Nie ma takiego zwierzaka: {clean}"
                        )
                    valid_villagers.append(villager)
                    try:
                        Residency.create(villager=villager, acprofile=island)
                    except IntegrityError:
                        transaction.rollback()
                        raise RzepaException(
                            f"{villager.name} jest już na twojej " f"wyspie."
                        )
        if len(valid_villagers) > 1:
            return await ctx.send(
                f"🏕 {ctx.author.mention}, zarejestrowano "
                f"{len(valid_villagers)} nowych mieszkańców "
                f"twojej wyspy."
            )
        v = valid_villagers[0]
        return await ctx.send(
            ctx.author.mention,
            embed=Embed(colour=0x8AD88A)
            .add_field(
                name=f"🏕 Zarejestrowano nowego mieszkańca twojej wyspy 🏕",
                value=v.link,
            )
            .set_thumbnail(v.image_url),
        )

    @commands.command(
        aliases=[
            "wyprowadź",
            "wyprowadz",
            "wyrzuć",
            "wyrzuc",
            "wyjeb",
            "wypierdol",
        ]
    )
    async def move_out(self, ctx: commands.Context, *, zwierzaki: str):
        """
        Usuwa 1 lub więcej mieszkańców (rozdzielonych przecinkami) z wyspy.
        """
        villagers = [z.strip() for z in zwierzaki.split(",")]
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
            island, created = Island.get_or_create(villager=user)
            residencies = []
            for v in villagers:
                residency = (
                    Residency.select()
                    .join(Villager)
                    .where(Residency.acprofile == island, Villager.name ** v)
                    .first()
                )
                if not residency:
                    clean = await commands.clean_content().convert(ctx, v)
                    raise RzepaException(
                        f"{ctx.author.mention}, na twojej wyspie "
                        f"nie ma zwierzaka: {clean}"
                    )
                residencies.append(residency)
            for residency in residencies:
                residency.delete_instance()
        message = ctx.invoked_with.replace("dź", "dz").replace("ć", "c")
        if message == "wyjeb":
            message = "wyjebano"
        else:
            message = message + "ono"

        if len(villagers) > 1:
            return await ctx.send(
                f"🏕 {ctx.author.mention}, {message} z twojej wyspy "
                f"{len(villagers)} zwierzaków."
            )
        return await ctx.send(
            ctx.author.mention,
            embed=Embed(colour=0x8AD88A)
            .add_field(
                name=f"🏕 {message.capitalize()} z twojej wyspy zwierzaka 🏕",
                value=residency.villager.link,
            )
            .set_thumbnail(residency.villager.image_url),
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
            db_user, _ = get_user_and_guild(user.id, ctx.guild, db)
            island = Island.select().where(Island.villager == db_user).first()
            item = None
            hot_item = (
                HotItem.select(HotItem.item)
                .where(HotItem.user == db_user)
                .first()
            )
            if hot_item:
                item = hot_item.item
            dodocode = None
            if ctx.guild is not None:
                code = (
                    DodoCode.select(DodoCode.code)
                    .join(User)
                    .switch(DodoCode)
                    .join(Guild)
                    .where(
                        Guild.discord_id == ctx.guild.id,
                        User.discord_id == user.id,
                    )
                    .first()
                )
                if code:
                    dodocode = code.code
        if not island:
            raise RzepaException(
                f"Użytkownik {user.display_name} nie ma profilu."
            )
        embed = format_profile(island, user, dodocode, item)
        return await ctx.send(
            f"️🏝 **Profil użytkownika {user.display_name}** 🏝", embed=embed
        )

    @commands.command(aliases=["item", "iotd", "hotitem"])
    async def hot_item(self, ctx: commands.Context, *, item: Optional[str]):
        """
        Ustawia Hot Item. Bez argumentów, wyświetla dzisiejsze hot itemy na tym serwerze.
        """
        t = tznow_dt()
        with db:
            if not item:
                # get all
                if not ctx.guild:
                    raise commands.NoPrivateMessage()
                g: DiscordGuild = ctx.guild
                hot_items = (
                    HotItem.select(HotItem.item, User.discord_id)
                    .join(User)
                    .join(GuildMembership)
                    .join(Guild)
                    .where(
                        Guild.discord_id == g.id,
                        HotItem.timestamp.day == t.day,
                        HotItem.timestamp.month == t.month,
                    )
                    .distinct(True)
                    .tuples()
                )
                s = f"📦 **Gorące przedmioty na {t.format('LL')}** 📦\n\n"
                messages = []
                for i in hot_items:
                    user = g.get_member(i[1])
                    if not user:
                        continue
                    line = f"**{user.display_name}**: {i[0]}\n"
                    if len(s + line) > 1998:
                        messages.append(s)
                        s = ""
                    s += line
                messages.append(s)
                for message in messages:
                    return await ctx.send(message)
            # set
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
            item = await commands.clean_content().convert(ctx, item)
            HotItem.delete().where(HotItem.user == user).execute()
            HotItem.create(user=user, item=item)
            return await ctx.send(
                f"📦 Zarejestrowano twój dzisiejszy Hot Item: `{item}`"
            )
