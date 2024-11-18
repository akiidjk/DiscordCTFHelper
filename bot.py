import os
import platform
import random
from pathlib import Path

import aiofiles
import aiosqlite
import discord
from discord import EventStatus, ScheduledEvent
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv

from database import DatabaseManager
from lib.logger import logger

intents = discord.Intents.all()


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            help_command=None,
        )
        """
        This creates custom bot variables so that we can access these variables in cogs more easily.

        For example, The config is available using the following code:
        - self.config # In this class
        - bot.config # In this file
        - self.bot.config # In cogs
        """
        self.logger = logger
        self.database = None

    async def init_db(self) -> None:
        db_path = Path(__file__).parent / "database" / "database.db"
        schema_path = Path(__file__).parent / "database" / "schema.sql"
        async with aiosqlite.connect(str(db_path)) as db:
            async with aiofiles.open(schema_path) as file:
                script = await file.read()
                await db.executescript(script)
            await db.commit()

    async def load_cogs(self) -> None:
        """
        The code in this function is executed whenever the bot will start.
        """
        cogs_path = Path(__file__).parent / "cogs"
        for file in cogs_path.glob("*.py"):
            extension = file.stem
            try:
                await self.load_extension(f"cogs.{extension}")
                self.logger.info(f"Loaded extension '{extension}'")
            except (commands.ExtensionError, ImportError):
                self.logger.exception(f"Failed to load extension {extension}")

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        """
        Setup the game status task of the bot.
        """
        statuses = [
            "Setting up your CTF events...",
            "Syncing with CTFTime's latest info...",
            "Retrieving event details from CTFTime...",
            "Preparing for your next CTF event...",
        ]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))  # noqa: S311

    @status_task.before_loop
    async def before_status_task(self) -> None:
        """
        Before starting the status changing task, we make sure the bot is ready
        """
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """
        Will just be executed when the bot starts the first time.
        """
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        self.logger.info("-------------------")
        await self.load_cogs()
        await self.init_db()
        synced = await self.tree.sync()
        self.logger.info(f"Synced {len(synced)} commands: {', '.join([sync.name for sync in synced])}")
        self.database = DatabaseManager(connection=await aiosqlite.connect(str(Path(__file__).parent / "database" / "database.db")))

    async def on_message(self, message: discord.Message) -> None:
        """
        The code in this event is executed every time someone sends a message, with or without the prefix

        :param message: The message that was sent.
        """
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs")

    async def on_command_error(self, context: Context, error) -> None:
        """
        The code in this event is executed every time a normal valid command catches an error.

        :param context: The context of the normal command that failed executing.
        :param error: The error that has been faced.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",  # noqa: E501
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(description="You are not the owner of the bot!", color=0xE02B2B)
            await context.send(embed=embed)
            if context.guild:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."  # noqa: E501
                )
            else:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."  # noqa: E501
                )
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="You are missing the permission(s) `" + ", ".join(error.missing_permissions) + "` to execute this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `" + ", ".join(error.missing_permissions) + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error

    async def on_scheduled_event_update(self, before: ScheduledEvent, after: ScheduledEvent) -> None:
        """
        Handles updates to scheduled events in Discord.

        Args:
            before (ScheduledEvent): Before the update
            after (ScheduledEvent): After the update

        """
        if before.status != after.status and after.status == EventStatus.active:
            ctf = await self.database.get_ctf_by_name(after.name, after.guild.id)

            if ctf is None:
                logger.info(f"CTF {after.name=} not found in database")
                return

            channel = self.get_channel(ctf.text_channel_id)

            await channel.send(f"<@&{ctf.role_id}> The CTF has started! Good luck to all participants! :tada:")

        if before.status != after.status and after.status == EventStatus.completed:
            ctf = await self.database.get_ctf_by_name(after.name, after.guild.id)

            if ctf is None:
                logger.info(f"CTF {after.name} not found in database")
                return

            channel = self.get_channel(ctf.text_channel_id)
            role = after.guild.get_role(ctf.role_id)

            server = await self.database.get_server_by_id(after.guild.id)

            await channel.edit(category=after.guild.get_channel(server.archive_category_id))

            await role.edit(color=discord.Color.light_gray(), hoist=False, mentionable=False)

            await channel.send(f"The CTF **{ctf.name}** has ended! The channel has been moved to the archived category.")

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """
        Handles the event when a reaction is added to a message.

        Args:
            reaction (discord.Reaction): The reaction that was added
            user (discord.Member): The user that added the reaction

        """
        if user.bot:
            return

        self.logger.debug(f"{reaction=}, {user=}")

        message = reaction.message
        ctf = await self.database.get_ctf_by_message_id(message.id, message.guild.id)
        if ctf is None:
            logger.info(f"CTF not found for message {message.id}")
            return
        role = message.guild.get_role(ctf.role_id)
        await user.add_roles(role)

    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """
        Handles the event when a reaction is removed from a message.

        Args:
            reaction (discord.Reaction): The reaction that was removed
            user (discord.Member): The user that removed the reaction

        """
        if user.bot:
            return

        self.logger.debug(f"{reaction=}, {user=}")

        message = reaction.message
        ctf = await self.database.get_ctf_by_message_id(message.id, message.guild.id)
        if ctf is None:
            logger.info(f"CTF not found for message {message.id}")
            return
        role = message.guild.get_role(ctf.role_id)
        await user.remove_roles(role)


load_dotenv()

bot = DiscordBot()
bot.run(os.getenv("TOKEN"))
