import asyncio
import contextlib

import discord
from discord.ext import commands
from glocklib import properties


# MPL v2 https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/context.py
class _ContextDBAcquire:
    __slots__ = ('ctx', 'timeout')

    def __init__(self, ctx, timeout):
        self.ctx = ctx
        self.timeout = timeout

    def __await__(self):
        return self.ctx._acquire(self.timeout).__await__()

    async def __aenter__(self):
        await self.ctx._acquire(self.timeout)
        return self.ctx.db

    async def __aexit__(self, *args):
        await self.ctx.release()


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection = None
        self.permissions = None
        self._db = None
        self.pool = self.bot.pool

    async def is_allowed(self):
        if self.permissions is None:
            return True

        if await self.bot.is_owner(self.author):
            return True

        return self.permissions.allowed or self.permissions.admin

    async def timeout(self, *, delete_after=15):
        """
        Sends a timeout message.
        """
        await self.send(
            'This has been closed due to a timeout {0}.'.format(self.author.mention),
            delete_after=delete_after,
        )

    async def show_help(self, command=None):
        cmd = self.bot.get_command('help')
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)

    async def get_dm(self, user=None):
        if user is None:
            user = self.author
        if user.dm_channel is None:
            await user.create_dm()
        return user.dm_channel

    async def delete(self, *, throw_error=False):
        """
        If throw error is false, it will send true/false if success.
        """
        if throw_error:
            await self.message.delete
        else:
            try:
                await self.message.delete()
            except discord.HTTPException:
                return False
        return True

    @property
    def db(self):
        return self._db if self._db else self.pool

    def acquire(self, *, timeout=300.0):
        """Acquires a database connection from the pool. e.g. ::
            async with ctx.acquire():
                await ctx.db.execute(...)
        or: ::
            await ctx.acquire()
            try:
                await ctx.db.execute(...)
            finally:
                await ctx.release()
        """
        return _ContextDBAcquire(self, timeout)

    async def release(self):
        """Releases the database connection from the pool.
        Useful if needed for "long" interactive commands where
        we want to release the connection and re-acquire later.
        Otherwise, this is called automatically by the bot.
        """
        # from source digging asyncpg source, releasing an already
        # released connection does nothing

        if self._db is not None:
            await self.bot.pool.release(self._db)
            self._db = None

    async def _acquire(self, timeout):
        if self._db is None:
            self._db = await self.pool.acquire(timeout=timeout)
        return self._db

    async def check(self, action_result):
        if action_result == 0 or action_result is True:
            em = '????'
        elif action_result == 2 or action_result is None:
            em = '<:eyee:840634640549281802>'
        elif action_result == 1 or action_result is False:
            em = '????'
        await self.message.add_reaction(em)

    def create_embed(self, description=discord.Embed.Empty, *, title=discord.Embed.Empty, error=False):
        cmd: commands.Command = self.command
        command_name = '{0} => '.format(cmd.cog_name)
        subs = cmd.qualified_name.split(' ')
        command_name += ' > '.join(subs)
        embed = discord.Embed(
            title=title,
            description=description,
            colour=discord.Colour.red() if error else properties.main_colour,
        )
        embed.set_author(name=command_name)
        embed.set_footer(text=str(self.author), icon_url=self.author.avatar_url)
        return embed

    async def ask(self, message=None, *, timeout=60, delete_after=True, author_id=None, allow_none=False, embed=None):
        """
        A function to ask a certain user for an answer using yes/no.
        :param embed: Another argument for the message.
        :param message: String for what the question is.
        :param timeout: How long the bot will wait for.
        :param delete_after: Should the message be deleted after?
        :param author_id: Who should respond. If None it will default to context author.
        :param allow_none: If they can respond with 'none'.
        :return: The author's answer. Returns None if timeout, and False if allow_none is on.
        """
        answer = None
        if message is None and embed is None:
            raise ValueError("Message and embed can't be NoneType!")

        message = await self.send(content=message, embed=embed)

        if author_id is None:
            author_id = self.author.id

        def check(msg):
            nonlocal answer
            if msg.author.id != author_id or msg.channel != message.channel:
                return False

            content = msg.content.lower()
            if "none" == content and allow_none:
                answer = False
                return True

            answer = msg.content
            return True

        try:
            answermsg = await self.bot.wait_for('message', timeout=timeout, check=check)
            if delete_after:
                with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                    await answermsg.delete()
        except asyncio.TimeoutError:
            answer = None

        if delete_after:
            with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                await message.delete()

        return answer

    async def reaction(self, message=None, *, embed=None, author_id=None, timeout=60, delete_after=True):
        emoji = None
        if message is None and embed is None:
            raise ValueError("Message and embed can't be NoneType!")

        message = await self.send(content=message, embed=embed)

        if author_id is None:
            author_id = self.author.id

        def check(reaction, user):
            nonlocal emoji
            if user.id != author_id or reaction.message.channel != message.channel:
                return False

            emoji = reaction.emoji
            return True

        try:
            await self.bot.wait_for('reaction_add', timeout=timeout, check=check)
        except asyncio.TimeoutError:
            emoji = None

        if delete_after:
            with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                await message.delete()

        return emoji
