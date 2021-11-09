import logging
import math
import traceback
from datetime import datetime

import discord
from discord.ext import commands

from glocklib import command_config
from glocklib.context import Context
from glocklib.help import HelpCommand

startup_extensions = (
    'glocklib.command_config',
)


class Bot(commands.Bot):

    def __init__(self, pool, *args, **kwargs):
        self.pool = pool
        self.tags = kwargs.pop('tags', True)
        self.context = kwargs.pop('context', Context)
        super().__init__(*args, **kwargs)
        self.help_command = HelpCommand()
        for extension in startup_extensions:
            try:
                self.load_extension(extension)
            except (discord.ClientException, ModuleNotFoundError):
                logging.warning('Failed to load extension {0}.'.format(extension))
                traceback.print_exc()

    async def on_command_error(self, ctx, error, *, raise_err=True):  # noqa: WPS217
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.CommandOnCooldown):
            if await self.is_owner(ctx.author):
                # We don't want the owner to be on cooldown.
                await ctx.reinvoke()
                return
            # Let people know when they can retry
            embed = ctx.create_embed(
                title='Command On Cooldown!',
                description='This command is currently on cooldown. Try again in `{0}` seconds.'.format(math.ceil(error.retry_after)),
                error=True,
            )
            await ctx.delete()
            await ctx.send(embed=embed, delete_after=5)
            return
        if raise_err:
            raise error

    async def process_commands(self, message):
        if message.author.bot:
            return
        tags = []
        if self.tags:
            if '--' in message.content:
                split = message.content.split('--')
                message.content = split[0]
                tags = split[1:]
                tags = [tag.lower().strip() for tag in tags]
            if r'\-\-' in message.content:
                message.content = message.content.replace(r'\-\-', '--')
                message = message.replace

        ctx: Context = await self.get_context(message, cls=self.context)

        if ctx.command is None:
            return

        ctx = await self.pre_process_tags(message, ctx, tags)
        # TODO Context doesn't walk through groups so only the base command is ever shown...
        ctx.permissions = await command_config.get_perms(self, ctx)

        if not await ctx.is_allowed():
            return

        try:
            await self.invoke(ctx)
        finally:
            await ctx.release()

        await self.process_tags(message, ctx, tags)

    async def pre_process_tags(self, message, ctx, tags):
        if 'time' in tags:
            ctx.start = datetime.now()
        if 'help' in tags:
            message.content = ctx.prefix + 'help ' + ctx.command.qualified_name
            ctx = await self.get_context(message, cls=Context)
        return ctx

    async def process_tags(self, message, ctx, tags):
        if 'info' in tags:
            embed = ctx.create_embed()
            embed.add_field(name='Prefix', value=ctx.prefix or 'None')
            embed.add_field(name='Command', value=ctx.command.qualified_name)
            if not isinstance(ctx.channel, discord.DMChannel):
                embed.add_field(name='Channel', value='<#{0}>'.format(ctx.channel.id))
            embed.add_field(name='Content', value=message.content)
            await ctx.send(embed=embed)
        if 'time' in tags:
            dif = (datetime.now() - ctx.start)
            await ctx.send(embed=ctx.create_embed(
                'Took `{0:.3g}` seconds!'.format(dif.total_seconds() + dif.microseconds / 1000000)),
            )

    def get_cog(self, name):
        lower = name.lower()
        for cog in self.cogs.keys():
            if cog.lower() == lower:
                return self.cogs[cog]
        return None
