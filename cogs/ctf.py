import json
import re
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands
from discord import CategoryChannel, TextChannel
from discord.ext.commands import Context

import requests

from api.ctftime import get_ctf_info
from lib.logger import logger


def check_url(url: str) -> bool:
    """
    Check if the URL is valid.

    :param url: The URL to check.
    :return: True if the URL is valid, False otherwise.
    """
    return bool(re.match(r"^https://ctftime.org/event/\d+/$", url))


class CTF(commands.Cog, name="CTF"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.category_active_id = None
        self.category_archived_id = None

    async def create_events(
        self,
        context: Context,
        event_name: str,
        event_description: str,
        start_time: datetime,
        end_time: datetime,
        logo: str = None,
        url: str = None,
        channel: TextChannel = None,
    ) -> None:
        """
        Create the events for the CTF.

        :param context: The application command context.
        :param event_name: The name of the event.
        :param event_description: The description of the event.
        :param channel: The channel where the event will be created.
        :param start_time: The start time of the event.
        :param end_time: The end time of the event.
        """
        guild = context.guild
        try:
            scheduled_event = await guild.create_scheduled_event(
                name=event_name,
                description=event_description
                + f"\n\nThe event will be take in the channel: {channel.name} | {channel.id}.",
                start_time=start_time,
                end_time=end_time,
                entity_type=discord.EntityType.external,
                location=url,
                privacy_level=discord.PrivacyLevel.guild_only,
                image=requests.get(logo).content
                if logo
                else open("images/default.png", "rb").read(),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            await context.send(
                f"Failed to create the event. ❌\n Error: {e}",
                ephemeral=True,
            )
            return
        return scheduled_event

    async def create_channel(
        self,
        context: Context,
        channel_name: str,
        category_id: int,
    ) -> TextChannel:
        guild = context.guild
        category = context.guild.get_channel(category_id)
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
            )
            overwrites = category.overwrites
            await channel.edit(overwrites=overwrites)
        except Exception as e:
            logger.error(f"Error: {e}")
            await context.send(
                f"Failed to create the channel or assign the permission. ❌\n Error: {e}",
                ephemeral=True,
            )
            return
        return channel

    def set_cat(self) -> bool:
        try:
            with open("config.json", "r") as config:
                json_data = json.load(config)
                self.category_active_id = json_data["ctf"]["category_active_id"]
                self.category_archived_id = json_data["ctf"]["category_archived_id"]
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    @commands.hybrid_command(
        name="set_category",
        description="Set the category for the active and archived CTF.",
    )
    @app_commands.describe(
        category_archived="The name of the category for the archived ctf",
        category_active="The name of the category for the next or current ctf",
    )
    async def init(
        self,
        context: Context,
        category_archived: CategoryChannel,
        category_active: CategoryChannel,
    ) -> None:
        """
        This is command simply set in the file the category for the active CTF and the category for the archived CTF.

        :param context: The application command context.
        :param category_archived: The category for the archived CTF.
        :param category_active: The category for the active CTF.
        """

        id_active = category_active.id
        id_archived = category_archived.id
        self.category_active_id = category_active
        self.category_archived_id = category_archived

        with open("config.json", "r") as config:
            json_data = json.load(config)
            json_data["ctf"]["category_active_id"] = id_active
            json_data["ctf"]["category_archived_id"] = id_archived

        with open("config.json", "w") as config:
            json.dump(json_data, config, indent=4)

        await context.send(
            content=f"Successfully! set the category for the active CTF to {category_active.name} and the category for the archived CTF to {category_archived.name}. ✅",
            ephemeral=True,
        )

    @commands.hybrid_command(
        name="get_info",
        description="Get the info for a events from ctftime.org",
    )
    @app_commands.describe(
        url="The URL of the event",
    )
    async def get_info(self, context: Context, url: str) -> None:
        """
        Get the information of a CTF from ctftime.org.

        :param context: The application command context.
        :param url: The URL of the CTF.
        """

        result = check_url(url)

        if not result:
            await context.send(
                "The URL is not valid. ❌ (The url must be in the format https://ctftime.org/event/<id>/)",
                ephemeral=True,
            )
            return

        data = get_ctf_info(url)

        start_time = datetime.fromisoformat(data["start"])
        end_time = datetime.fromisoformat(data["finish"])

        if not self.category_active_id:
            res = self.set_cat()
            if not res:
                await context.send(
                    "Failed to set the category. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        channel = await self.create_channel(
            context=context,
            channel_name=data["title"] + " - " + f"{str(start_time.year)}",
            category_id=self.category_active_id,
        )

        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            url=data["url"],
            timestamp=datetime.now(),
            color=0xBEBEFE,
        )
        await channel.send(embed=embed)

        logger.debug(f"Logo: {data['logo']}")

        await self.create_events(
            context=context,
            event_name=data["title"],
            event_description=data["description"],
            start_time=start_time,
            end_time=end_time,
            url=data["url"],
            channel=channel,
            logo=data["logo"] if data["logo"] != "" in data else None,
        )

        await context.send("Ctf created in the discord server ✅", ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(CTF(bot))
