# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

import asyncio
import itertools
import logging
from datetime import datetime
import traceback
import discord
import re
from discord.ext import commands
from discord.utils import oauth_url

from rzepabot.config import RZEPABOT_PERMS
from rzepabot.exceptions import RzepaException
from rzepabot.persistence import Guild, db, cleanup
from rzepabot.plugins.dodokod import Dodokod
from rzepabot.plugins.profile import Profil
from rzepabot.plugins.info import Info
from rzepabot.presence import get_presence, schedule_next_change

logger = logging.getLogger()

pl = logging.getLogger("peewee")
pl.addHandler(logging.StreamHandler())
pl.setLevel(logging.DEBUG)


class RzepabotHelpPaginator(commands.Paginator):
    def __init__(self):
        super().__init__("", "")

    def add_line(self, line="", *, empty=False):
        self._current_page.append(line)

    def close_page(self):
        self._pages.append("\n".join(self._current_page))
        self._current_page = []
        self._count = 0


class RzepaBotHelp(commands.DefaultHelpCommand):
    def shorten_text(self, text):
        return text

    def get_ending_note(self):
        command_name = self.invoked_with
        return (
            f"Wpisz `{self.clean_prefix}{command_name} <nazwa komendy>` aby "
            f"dowiedzieć się więcej o danej komendzie.\n "
            f"Możesz również wpisać `{self.clean_prefix}{command_name}` "
            f"aby dowiedzieć się więcej o całej kategorii.\n\n"
            f"Komendy można wywoływać też podając tylko ich pierwszą literę."
        )

    def command_not_found(self, string):
        return f'Nie znaleziono komendy "{string}".'

    def subcommand_not_found(self, command, string):
        if (
            isinstance(command, commands.Group)
            and len(command.all_commands) > 0
        ):
            return f'Grupa "{command.qualified_name}" nie ma komendy {string}'
        return f'Komenda "{command}" nie ma subkomend.'

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 1:
            fmt = f"[{'|'.join(command.aliases)}]"
            if parent:
                fmt = parent + " " + fmt
            alias = fmt
        elif len(command.aliases) > 0:
            fmt = command.aliases[0]
            if parent:
                fmt = parent + " " + fmt
            alias = fmt
        else:
            alias = command.name if not parent else parent + " " + command.name

        return "`%s%s %s`" % (self.clean_prefix, alias, command.signature)

    def add_indented_commands(self, commands, *, heading, max_size=None):
        if not commands:
            return

        self.paginator.add_line(heading)
        max_size = max_size or self.get_max_size(commands)

        get_width = discord.utils._string_width
        for command in commands:
            if len(command.aliases) > 0:
                name = f"`{command.aliases[0]}`"
            else:
                name = f"`{command.name}`"
            width = max_size - (get_width(name) - len(name))
            entry = "{0}{1:<{width}} {2}".format(
                self.indent * " ", name, command.short_doc, width=width
            )
            self.paginator.add_line(self.shorten_text(entry))

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            # <description> portion
            self.paginator.add_line(bot.description, empty=True)

        no_category = "\u200b**{0.no_category}**:".format(self)

        def get_category(command, *, no_category=no_category):
            cog = command.cog
            return (
                f"**{cog.qualified_name}**:"
                if cog is not None
                else no_category
            )

        filtered = await self.filter_commands(
            bot.commands, sort=True, key=get_category
        )
        max_size = self.get_max_size(filtered)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = (
                sorted(commands, key=lambda c: c.name)
                if self.sort_commands
                else list(commands)
            )
            self.add_indented_commands(
                commands, heading=category, max_size=max_size
            )

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()


class RzepaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=RzepaBot.get_prefixes)
        self.help_command = RzepaBotHelp(
            commands_heading="\n**Komendy**",
            no_category="Brak kategorii",
            paginator=RzepabotHelpPaginator(),
        )
        self.add_cog(Dodokod(self))
        self.add_cog(Info(self))
        self.add_cog(Profil(self))

    def get_prefixes(self, _):
        return [self.user.mention, "$"]

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        print(oauth_url(self.user.id, discord.Permissions(RZEPABOT_PERMS)))
        with db:
            guild_ids = Guild.select(Guild.discord_id)
            joined_guilds = [g.id for g in self.guilds]
            for guild in guild_ids:
                if guild.discord_id not in joined_guilds:
                    guild.delete_instance()
        self.loop.create_task(self.manage_presence())

    async def manage_presence(self):
        while True:
            presence = get_presence()
            await self.change_presence(activity=presence)
            await asyncio.sleep(schedule_next_change(datetime.now()))

    async def cleanup(self):
        while True:
            cleanup()
            await asyncio.sleep(60 * 60)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, RzepaException):
                return await ctx.send(f"⚠️ {error.original.message}")
        elif isinstance(error, commands.NoPrivateMessage):
            return await ctx.send(
                "⚠️ Ta komenda może być użyta tylko na serwerze."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, musisz podać argument: `{error.param.name}`."
            )
        elif isinstance(error, commands.BadArgument):
            if match := re.match('^Member "(.*)" not found$', error.args[0]):
                return await ctx.send(
                    f'⚠️ Użytkownik "{match.group(1)}" nie istnieje.'
                )
        traceback.print_exception(type(error), error, error.__traceback__)
