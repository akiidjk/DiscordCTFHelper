import json
from datetime import datetime

from discord.ext import commands
from discord import Color, Embed, EntityType, Message, PrivacyLevel, Role, app_commands
from discord import CategoryChannel, TextChannel
from discord.ext.commands import Context

from lib.logger import logger
from lib.ctf_model import CTFModel
from lib.utils import check_url, get_logo, get_ctf_info


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
        logo: str,
        url: str,
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
        logger.debug(f"{logo=}")
        logger.debug(f"{type(logo)=}")

        image_logo = await get_logo(logo)

        try:
            scheduled_event = await guild.create_scheduled_event(
                name=event_name,
                description=event_description,
                start_time=start_time,
                end_time=end_time,
                entity_type=EntityType.external,
                location=url,
                privacy_level=PrivacyLevel.guild_only,
                image=image_logo,
            )
        except Exception as e:
            logger.error(f"Error: {e}")

            if str(e) == "Unsupported image type given":
                return await self.create_events(
                    context=context,
                    event_name=event_name,
                    event_description=event_description,
                    start_time=start_time,
                    end_time=end_time,
                    url=url,
                    logo=None,
                )

            await context.send(
                f"Failed to create the event. ❌\n Error: {e}",
                ephemeral=True,
            )

            return
        return scheduled_event

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

    async def create_channel(
        self,
        context: Context,
        channel_name: str,
        category_id: int,
    ) -> TextChannel:
        guild = context.guild
        category = context.guild.get_channel(category_id)
        logger.debug(f"{category=}")
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

    async def create_embed(self,
        data: dict, start_time: datetime, end_time: datetime, channel: TextChannel
    ) -> Message:
        description = f"""
**Description:**

{data["description"]}

- **Start Time:** <t:{int(start_time.timestamp())}:f>
- **End Time:** <t:{int(end_time.timestamp())}:f>
- **URL:** {data["url"]}
- **Format:** {data["format"]}
- **Location:** {data["location"]}
- **Weight:** {data["weight"]}
- **Prizes:**\n{data["prizes"]}

"""

        embed = (
            Embed(
                title=data["title"],
                description=description,
                url=data["url"],
                timestamp=datetime.now(),
                color=0xBEBEFE,
            )
            .set_thumbnail(url=data["logo"])
            .set_footer(
                text="Add a reaction to get the ctf role (only if you want to participate). 🙃",
                icon_url=None,
            )
        )

        msg = await channel.send(embed=embed)

        await msg.add_reaction("✅")

        return msg

    async def create_role(self, context: Context, name: str) -> Role:
        guild = context.guild
        role = await context.guild.create_role(
            name=name,
            color=Color.random(),
            mentionable=True,
            hoist=True,
        )

        bot_top_role = guild.me.top_role

        manageable_roles = [
            role for role in guild.roles if role.position < bot_top_role.position
        ]

        logger.debug(
            [str(role.position) + " " + str(role.name) for role in manageable_roles]
        )

        lowest_manageable_role = max(manageable_roles, key=lambda r: r.position)

        new_position = max(
            lowest_manageable_role.position + 1, bot_top_role.position - 1
        )

        logger.debug(f"{new_position=}")

        await guild.edit_role_positions({role: new_position})

        return role

    # * -----------------------------------------------------------------------

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
        self.category_active_id = id_active
        self.category_archived_id = id_archived

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

    # * -----------------------------------------------------------------------

    @commands.hybrid_command(
        name="create_ctf",
        description="Create a CTF event in the discord server.",
    )
    @app_commands.describe(
        url="The URL of the event",
    )
    async def create_ctf(self, context: Context, url: str) -> None:
        """
        Create a CTF event in the discord server.

        :param context: The application command context.
        :param url: The URL of the CTF.
        """
        await context.defer(ephemeral=True)
        result = check_url(url)

        if not result:
            await context.send(
                "The URL is not valid. ❌ (The url must be in the format https://ctftime.org/event/<id>)",
                ephemeral=True,
            )
            return

        data = get_ctf_info(url)

        start_time = datetime.fromisoformat(data["start"])
        end_time = datetime.fromisoformat(data["finish"])

        data["title"] = data["title"] + " - " + f"{str(start_time.year)}"

        if await self.bot.database.is_ctf_present(data["title"]):
            await context.send(
                "The CTF is already present in the discord server. ❌",
                ephemeral=True,
            )
            return

        logger.debug(f"{self.category_active_id=}")

        if not self.category_active_id:
            res = self.set_cat()
            if not res:
                await context.send(
                    "Failed to set the category. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        logger.debug(f"{self.category_active_id=}")

        channel = await self.create_channel(
            context=context,
            channel_name=data["title"],
            category_id=self.category_active_id,
        )

        logger.debug(f"{channel=}")

        msg = await self.create_embed(
            data=data,
            start_time=start_time,
            end_time=end_time,
            channel=channel,
        )

        description = (
            str(data["description"])[:997] + "..."
            if len(data["description"]) >= 997
            else data["description"]
        )

        logger.debug(f"{data['logo']=}")
        logger.debug(f"{data['logo'] != ''=}")

        events = await self.create_events(
            context=context,
            event_name=data["title"],
            event_description=description,
            start_time=start_time,
            end_time=end_time,
            url=data["url"],
            logo=data["logo"],
        )

        role = await self.create_role(
            context=context,
            name=data["title"],
        )

        logger.debug(f"{msg.id=}")

        ctf = CTFModel(
            name=data["title"],
            description=data["description"],
            text_channel_id=channel.id,
            event_id=events.id,
            role_id=role.id,
            msg_id=msg.id,
        )

        logger.debug(f"{ctf=}")

        await self.bot.database.add_ctf(ctf)

        await context.send("Ctf created in the discord server ✅", ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(CTF(bot))
