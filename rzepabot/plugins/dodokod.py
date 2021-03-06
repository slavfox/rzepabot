# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from typing import Optional

from discord.ext import commands
from peewee import JOIN
from pendulum import instance, timezone

from rzepabot.exceptions import RzepaException
from rzepabot.persistence import DodoCode, Island, User, db, get_user_and_guild

VALID_DODOCODE_CHARS = "1234567890QWERTYUPASDFGHJKLXCVBNM"


def validate_dodocode(dodocode: str):
    code = dodocode.upper().strip()
    for ch in code:
        if ch not in VALID_DODOCODE_CHARS:
            raise RzepaException(
                f"Niepoprawny dodokod: {code}. "
                f"Znak {repr(ch)} nie może występować w dodokodach."
            )
    if len(code) != 5:
        raise RzepaException(
            f"Niepoprawny dodokod: {code}. " "Dodokod musi mieć pięć znaków."
        )
    return code


class Dodokod(commands.Cog):
    """Komendy dotyczące otwierania wyspy dla gości."""

    @commands.command(aliases=["otwórz", "otworz", "o"])
    @commands.check(commands.guild_only())
    async def open(
        self,
        ctx: commands.Context,
        dodokod: Optional[str],
        komentarz: commands.Greedy[Optional[str]],
    ):
        """
        Rejestruje dodokod wyspy, z opcjonalnym komentarzem.

        Usuwa wcześniej zarejestrowane dodokody.
        """
        if not dodokod:
            return await self.list_open(ctx)
        code = validate_dodocode(dodokod)
        komentarz = await commands.clean_content().convert(
            ctx, " ".join(komentarz)
        )
        if len(komentarz) > 255:
            raise RzepaException(f"Ten komentarz jest zbyt długi!")

        with db:
            user, guild = get_user_and_guild(ctx.author.id, ctx.guild, db)
            # Clean up old dodocodes
            DodoCode.delete().where(
                DodoCode.user == user, DodoCode.guild_id == guild.id
            ).execute()
            DodoCode(
                user=user, guild=guild, code=code, comment=komentarz
            ).save()
        island = user.island.first()
        if island:
            island_name = island.island_name
        else:
            island_name = f"użytkownika {ctx.author.mention}"
        comment_notice = ""
        if komentarz:
            comment_notice = f' i komentarzem "{komentarz}"'
        return await ctx.send(
            f"🛫 Otwarto wyspę {island_name} z kodem "
            f"`{code}`{comment_notice}."
        )

    @commands.command(aliases=["zamknij"])
    @commands.check(commands.guild_only())
    async def close(self, ctx: commands.Context):
        """
        Zamyka wcześniej otwartą wyspę.
        """
        with db:
            user, _ = get_user_and_guild(ctx.author.id, ctx.guild, db)
            code = DodoCode.get_or_none(DodoCode.user == user)
            if not code:
                return await ctx.send(
                    f"{ctx.author.mention}, nie masz obecnie otwartej wyspy."
                )
            code.delete_instance()
            island = user.island.first()
            if island:
                island_name = island.island_name
            else:
                island_name = f"użytkownika {ctx.author.mention}"
            return await ctx.send(
                f"🛬 Zamknięto wyspę {island_name} z kodem" f" {code.code}."
            )

    @commands.command(aliases=["otwarte"])
    @commands.check(commands.guild_only())
    async def list_open(self, ctx: commands.Context):
        """
        Wypisuje informacje o otwartych wyspach na obecnym serwerze.
        """
        with db:
            user, guild = get_user_and_guild(ctx.author.id, ctx.guild, db)
            codes = (
                DodoCode.select(DodoCode, User, Island)
                .join(User)
                .join(Island, JOIN.LEFT_OUTER)
                .where(DodoCode.guild == guild)
                .objects()
            )
            lines = []
            for i, code in enumerate(codes, 1):
                if (island := code.user.island.first()) and island.island_name:
                    island_identifier = island.island_name
                else:
                    d_id = code.user.discord_id
                    user = ctx.guild.get_member(d_id)
                    island_identifier = (
                        f"Wyspa użytkownika **" f"{user.display_name}**"
                    )
                opened_at = instance(
                    code.timestamp, tz=timezone("Europe/Warsaw")
                ).diff_for_humans(locale="pl")
                comment = ""
                if code.comment:
                    comment = f', komentarz "{code.comment}"'
                lines.append(
                    f"{i}. `{code.code}`: {island_identifier} "
                    f"(otwarto **{opened_at}**{comment})\n"
                )

            if not lines:
                return await ctx.send(
                    ":no_entry: Na tym serwerze nie ma obecnie "
                    "otwartych wysp."
                )
            l = 0
            s = "🛫 **Otwarte wyspy** 🛬\n\n"
            messages = []
            for line in lines:
                if len(s + line) > 1998:
                    messages.append(s)
                    s = ""
                s += line
            messages.append(s)
            for message in messages:
                await ctx.send(message)
