from datetime import datetime, timezone, UTC

from discord import CategoryChannel, Color, Embed, EntityType, Message, PrivacyLevel, Role, TextChannel, app_commands
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands import Context

from lib.logger import logger
from lib.models import CTFModel, ServerModel
from lib.utils import check_url, get_ctf_info, get_logo

MAX_DESC_LENGTH = 997


class CTF(commands.Cog, name="CTF"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.category_active_id = None
        self.category_archived_id = None
        self.min_role_id = None

    async def create_events(
        self,
        context: Context,
        info: dict,
        event_description: str,
        start_time: datetime,
        end_time: datetime,
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
        image_logo = await get_logo(info["logo"])

        try:
            scheduled_event = await guild.create_scheduled_event(
                name=info["title"],
                description=event_description,
                start_time=start_time,
                end_time=end_time,
                entity_type=EntityType.external,
                location=info["url"],
                privacy_level=PrivacyLevel.guild_only,
                image=image_logo,
            )
        except HTTPException as e:
            logger.error(f"Error: {e}")

            if str(e) == "Unsupported image type given":
                return await self.create_events(
                    context=context,
                    info=info,
                    event_description=event_description,
                    start_time=start_time,
                    end_time=end_time,
                    logo=None,
                )

            await context.send(
                f"Failed to create the event. ❌\n Error: {e}",
                ephemeral=True,
            )

            return None
        return scheduled_event

    async def set_cat(self, server_id) -> bool:
        try:
            server = await self.bot.database.get_server_by_id(server_id)
            logger.debug(f"{server=}")
            self.category_active_id = server.active_category_id
            self.category_archived_id = server.archive_category_id
            self.min_role_id = server.min_role_id

        except HTTPException as e:
            logger.error(f"Error: {e}")
            return False
        else:
            return True

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
        except HTTPException as e:
            logger.error(f"Error: {e}")
            await context.send(
                f"Failed to create the channel or assign the permission. ❌\n Error: {e}",
                ephemeral=True,
            )
            return None
        return channel

    async def create_embed(self, data: dict, start_time: datetime, end_time: datetime, channel: TextChannel) -> Message:
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
                timestamp=datetime.now(tz=UTC),
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

        manageable_roles = [role for role in guild.roles if role.position < bot_top_role.position]

        logger.debug([str(role.position) + " " + str(role.name) for role in manageable_roles])

        lowest_manageable_role = max(manageable_roles, key=lambda r: r.position)

        new_position = max(lowest_manageable_role.position + 1, bot_top_role.position - 1)

        logger.debug(f"{new_position=}")

        await guild.edit_role_positions({role: new_position})

        return role

    # * -----------------------------------------------------------------------

    @commands.hybrid_command(
        name="set_category",
        description="Set the category for the active and archived CTF.",
    )
    @app_commands.describe(
        category_active="The name of the category for the next or current ctf",
        category_archived="The name of the category for the archived ctf",
        min_role="The minimum role required to run the create_ctf command",
    )
    async def init(
        self,
        context: Context,
        category_active: CategoryChannel,
        category_archived: CategoryChannel,
        min_role: Role,
    ) -> None:
        """
        Set the category for the active CTF and the category for the archived CTF in the file.

        :param context: The application command context.
        :param category_archived: The category for the archived CTF.
        :param category_active: The category for the active CTF.
        """
        if not context.author.guild_permissions.administrator:
            await context.send(
                "You need to be the admin of the server to run this command. ❌",
                ephemeral=True,
            )
            return

        id_active = category_active.id
        id_archived = category_archived.id
        min_role_id = min_role.id
        self.category_active_id = id_active
        self.category_archived_id = id_archived
        self.min_role_id = min_role_id

        logger.debug(f"{min_role_id=}")

        await self.bot.database.add_server(
            ServerModel(
                id=context.guild.id,
                active_category_id=id_active,
                archive_category_id=id_archived,
                min_role_id=min_role_id,
            )
        )

        await context.send(
            content=f"Successfully! set the category for the active CTF to {category_active.name} and the category for the archived CTF to {category_archived.name}. ✅",  # noqa: E501
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
        if not self.category_active_id or not self.min_role_id:
            res = await self.set_cat(server_id=context.guild.id)
            if not res:
                await context.send(
                    "Failed to set the category. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        min_role = context.guild.get_role(self.min_role_id)

        logger.debug(f"{min_role.position=}")
        logger.debug(f"{context.author.top_role.position=}")

        if context.author.top_role.position < min_role.position:
            await context.send(
                "You don't have the required role to run this command. ❌",
                ephemeral=True,
            )
            return

        await context.defer(ephemeral=True)
        result = check_url(url)

        if not result:
            await context.send(
                "The URL is not valid. ❌ (The url must be in the format https://ctftime.org/event/<id>)",
                ephemeral=True,
            )
            return

        data = await get_ctf_info(url)

        if not data:
            await context.send(
                "Failed to get the information of the CTF. ❌",
                ephemeral=True,
            )
            return

        start_time = datetime.fromisoformat(data["start"])
        end_time = datetime.fromisoformat(data["finish"])

        data["title"] = data["title"] + " - " + f"{start_time.year!s}"

        if await self.bot.database.is_ctf_present(data["title"], context.guild.id):
            await context.send(
                "The CTF is already present in the discord server. ❌",
                ephemeral=True,
            )
            return

        logger.debug(f"{self.category_active_id=}")

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

        description = str(data["description"])[:MAX_DESC_LENGTH] + "..." if len(data["description"]) >= MAX_DESC_LENGTH else data["description"]

        logger.debug(f"{data['logo']=}")
        logger.debug(f"{data['logo'] != ''=}")

        events = await self.create_events(
            context=context,
            info=data,
            event_description=description,
            start_time=start_time,
            end_time=end_time,
        )

        role = await self.create_role(
            context=context,
            name=data["title"],
        )

        logger.debug(f"{msg.id=}")

        ctf = CTFModel(
            server_id=context.guild.id,
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
