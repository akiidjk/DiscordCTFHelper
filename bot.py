import logging
import os
import platform
import random
import sys
from pathlib import Path

import aiofiles
import aiosqlite
import discord
from discord import CategoryChannel, EventStatus, ScheduledEvent, TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv

from database import DatabaseManager
from lib.logger import init_logger, logger

intents = discord.Intents.all()


levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            help_command=None,
        )
        self.logger = logger
        self.database: DatabaseManager | None = None

    async def init_db(self) -> None:
        db_path = Path(__file__).parent / "database" / "database.db"
        schema_path = Path(__file__).parent / "database" / "schema.sql"
        async with aiosqlite.connect(str(db_path)) as db:
            async with aiofiles.open(schema_path) as file:
                script = await file.read()
                await db.executescript(script)
            await db.commit()
        self.database = DatabaseManager(connection=await aiosqlite.connect(str(db_path)))

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
        """Setup the game status task of the bot."""
        statuses = [
            "Setting up your CTF events...",
            "Syncing with CTFTime's latest info...",
            "Retrieving event details from CTFTime...",
            "Preparing for your next CTF event...",
        ]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))

    @status_task.before_loop
    async def before_status_task(self) -> None:
        """Before starting the status changing task, we make sure the bot is ready"""
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """Will just be executed when the bot starts the first time."""
        if not self.user:
            return

        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        self.logger.info("-------------------")
        await self.load_cogs()
        await self.init_db()
        synced = await self.tree.sync()
        self.logger.info(f"Synced {len(synced)} commands: {', '.join([sync.name for sync in synced])}")

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages and process commands."""
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        """Log successful command executions."""
        if not context.command:
            return

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
        """Handle command errors with appropriate messages."""
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24

            time_strings = []
            if hours > 0:
                time_strings.append(f"{round(hours)} hours")
            if minutes > 0:
                time_strings.append(f"{round(minutes)} minutes")
            if seconds > 0:
                time_strings.append(f"{round(seconds)} seconds")

            time_string = " ".join(time_strings)

            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {time_string}.",
                color=0xE02B2B,
            )
            if context.channel:
                await context.send(embed=embed)

        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(description="You are not the owner of the bot!", color=0xE02B2B)
            if context.channel:
                await context.send(embed=embed)

            if context.guild:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
                )
            else:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
                )

        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description=f"You are missing the permission(s) `{', '.join(error.missing_permissions)}` to execute this command!",
                color=0xE02B2B,
            )
            if context.channel:
                await context.send(embed=embed)

        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description=f"I am missing the permission(s) `{', '.join(error.missing_permissions)}` to fully perform this command!",
                color=0xE02B2B,
            )
            if context.channel:
                await context.send(embed=embed)

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            if context.channel:
                await context.send(embed=embed)
        else:
            raise error

    async def on_scheduled_event_update(self, before: ScheduledEvent, after: ScheduledEvent) -> None:
        """Handle Discord scheduled event updates."""
        if not self.database or not after.guild:
            return

        if before.status != after.status and after.status == EventStatus.active:
            ctf = await self.database.get_ctf_by_name(after.name, after.guild.id)

            if ctf is None:
                logger.info(f"CTF {after.name=} not found in database")
                return

            channel = self.get_channel(ctf.text_channel_id)
            if isinstance(channel, TextChannel):
                await channel.send(f"<@&{ctf.role_id}> The CTF has started! Good luck to all participants! :tada:")

        if before.status != after.status and after.status == EventStatus.completed:
            ctf = await self.database.get_ctf_by_name(after.name, after.guild.id)

            if ctf is None:
                logger.info(f"CTF {after.name} not found in database")
                return

            channel = self.get_channel(ctf.text_channel_id)
            role = after.guild.get_role(ctf.role_id)
            server = await self.database.get_server_by_id(after.guild.id)

            if server and isinstance(channel, TextChannel):
                archive_category = after.guild.get_channel(server.archive_category_id)
                if isinstance(archive_category, CategoryChannel):
                    await channel.edit(category=archive_category)

                if role:
                    await role.edit(color=discord.Color.light_gray(), hoist=False, mentionable=False)

                await channel.send(f"<@&{ctf.role_id}> The CTF **{ctf.name}** has ended! The channel has been moved to the archived category.")

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """Handle adding reactions to messages."""
        if user.bot or not self.database:
            return

        self.logger.debug(f"{reaction=}, {user=}")

        message = reaction.message
        if not message.guild:
            return

        ctf = await self.database.get_ctf_by_message_id(message.id, message.guild.id)
        if ctf is None:
            logger.info(f"CTF not found for message {message.id}")
            return

        role = message.guild.get_role(ctf.role_id)
        if role:
            await user.add_roles(role)

    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """Handle removing reactions from messages."""
        if user.bot or not self.database:
            return

        self.logger.debug(f"{reaction=}, {user=}")

        message = reaction.message
        if not message.guild:
            return

        ctf = await self.database.get_ctf_by_message_id(message.id, message.guild.id)
        if ctf is None:
            logger.info(f"CTF not found for message {message.id}")
            return

        role = message.guild.get_role(ctf.role_id)
        if role:
            await user.remove_roles(role)
        else:
            logger.info(f"Role not found for CTF {ctf.name}")


if __name__ == "__main__":
    load_dotenv()

    if len(sys.argv) != 2 or sys.argv[1] not in levels:
        message = "Please provide a valid logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        raise ValueError(message)

    init_logger(level=levels[sys.argv[1]])
    bot = DiscordBot()
    TOKEN = os.getenv("TOKEN")
    if TOKEN is None:
        message = "Please provide a token in the .env file"
        raise ValueError(message)
    bot.run(TOKEN)
