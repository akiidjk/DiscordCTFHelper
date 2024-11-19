from datetime import UTC, datetime

from discord import CategoryChannel, Color, Embed, EntityType, Interaction, Message, PrivacyLevel, Role, TextChannel, app_commands
from discord.errors import HTTPException
from discord.ext import commands

from lib.logger import logger
from lib.models import CTFModel, ServerModel
from lib.utils import check_url, get_ctf_info, get_logo, sanitize_input

MAX_DESC_LENGTH = 997


class CTF(commands.Cog, name="CTF"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.category_active_id = None
        self.category_archived_id = None
        self.min_role_id = None

    async def create_events(
        self,
        interaction: Interaction,
        info: dict,
        event_description: str,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """
        Create a scheduled event in the discord server.

        Args:
            interaction (Interaction): The application command context.
            info (dict): The information of the CTF.
            event_description (str): The description of the event.
            start_time (datetime): The start time of the event.
            end_time (datetime): The end time of the event.

        """
        guild = interaction.guild
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
                    interaction=interaction,
                    info=info,
                    event_description=event_description,
                    start_time=start_time,
                    end_time=end_time,
                    logo=None,
                )

            await interaction.followup.send(
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
        except AttributeError as e:
            logger.error(f"Error: {e}")
            return False
        else:
            return True

    async def create_channel(
        self,
        interaction: Interaction,
        channel_name: str,
        category_id: int,
    ) -> TextChannel:
        guild = interaction.guild
        category = interaction.guild.get_channel(category_id)
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
            await interaction.followup.send(
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

    async def create_role(self, interaction: Interaction, name: str) -> Role:
        guild = interaction.guild

        color = Color.random()

        while color == Color.light_gray():
            color = color.random()

        role = await interaction.guild.create_role(
            name=name,
            color=Color.random(),
            mentionable=True,
            hoist=True,
        )

        min_permission_role = interaction.guild.get_role(self.min_role_id)

        manageable_roles = [role for role in guild.roles if role.position < min_permission_role.position]

        logger.debug([str(role.position) + " " + str(role.name) for role in manageable_roles])

        lowest_manageable_role = max(manageable_roles, key=lambda r: r.position)

        new_position = max(lowest_manageable_role.position + 1, min_permission_role.position - 1)

        logger.debug(f"{new_position=}")

        await guild.edit_role_positions({role: new_position})

        return role

    # * -----------------------------------------------------------------------

    @app_commands.command(
        name="init",
        description="Initialize the CTF bot in the discord server.",
    )
    @app_commands.describe(
        category_active="The name of the category for the next or current ctf",
        category_archived="The name of the category for the archived ctf",
        min_role="The minimum role required to run the create_ctf command",
    )
    async def init(
        self,
        interaction: Interaction,
        category_active: CategoryChannel,
        category_archived: CategoryChannel,
        min_role: Role,
    ) -> None:
        """
        Initialize the CTF bot in the discord server.

        Args:
            interaction (Interaction): The application command context.
            category_active (CategoryChannel): The name of the category for the next or current ctf
            category_archived (CategoryChannel): The name of the category for the archived ctf
            min_role (Role): The minimum role required to run the create_ctf command

        """
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(
                "You need to be the admin of the server to run this command. ❌",
                ephemeral=True,
            )
            return

        if await self.bot.database.get_server_by_id(interaction.guild.id):
            await self.bot.database.delete_server(interaction.guild.id)

        id_active = category_active.id
        id_archived = category_archived.id
        min_role_id = min_role.id
        self.category_active_id = id_active
        self.category_archived_id = id_archived
        self.min_role_id = min_role_id

        logger.debug(f"{min_role_id=}")

        await self.bot.database.add_server(
            ServerModel(
                id=interaction.guild.id,
                active_category_id=id_active,
                archive_category_id=id_archived,
                min_role_id=min_role_id,
            )
        )

        await interaction.followup.send(
            content=f"Successfully set the category for the active CTF to {category_active.name} and the category for the archived CTF to {category_archived.name}! ✅",  # noqa: E501
            ephemeral=True,
        )

    # * -----------------------------------------------------------------------

    @app_commands.command(
        name="create_ctf",
        description="Create a CTF event in the discord server.",
    )
    @app_commands.describe(
        url="The URL of the event",
    )
    async def create_ctf(self, interaction: Interaction, url: str) -> None:
        """
        Create a CTF event in the discord server.

        Args:
            interaction (Interaction): The application command context.
            url (str): The URL of the event

        """
        await interaction.response.defer(ephemeral=True)

        if not self.category_active_id or not self.min_role_id:
            res = await self.set_cat(server_id=interaction.guild.id)
            if not res:
                await interaction.followup.send(
                    "Failed to set the category. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        min_role = interaction.guild.get_role(self.min_role_id)

        logger.debug(f"{min_role.position=}")
        logger.debug(f"{interaction.user.top_role.position=}")

        if interaction.user.top_role.position < min_role.position:
            await interaction.followup.send(
                "You don't have the required role to run this command. ❌",
                ephemeral=True,
            )
            return

        result = check_url(url)

        if not result:
            await interaction.followup.send(
                "The URL is not valid. ❌ (The url must be in the format https://ctftime.org/event/<id>)",
                ephemeral=True,
            )
            return

        data = await get_ctf_info(url)

        if not data:
            await interaction.followup.send(
                "Failed to get the information of the CTF. ❌",
                ephemeral=True,
            )
            return

        start_time = datetime.fromisoformat(data["start"])
        end_time = datetime.fromisoformat(data["finish"])

        data["title"] = sanitize_input(data["title"])
        data["title"] = data["title"] + " - " + f"{start_time.year!s}"

        if await self.bot.database.is_ctf_present(data["title"], interaction.guild.id):
            await interaction.followup.send(
                "The CTF is already present in the discord server. ❌",
                ephemeral=True,
            )
            return

        logger.debug(f"{self.category_active_id=}")

        logger.debug(f"{self.category_active_id=}")

        channel = await self.create_channel(
            interaction=interaction,
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
            interaction=interaction,
            info=data,
            event_description=description,
            start_time=start_time,
            end_time=end_time,
        )

        role = await self.create_role(
            interaction=interaction,
            name=data["title"],
        )

        logger.debug(f"{msg.id=}")

        ctf = CTFModel(
            server_id=interaction.guild.id,
            name=data["title"],
            description=data["description"],
            text_channel_id=channel.id,
            event_id=events.id,
            role_id=role.id,
            msg_id=msg.id,
        )

        logger.debug(f"{ctf=}")

        await self.bot.database.add_ctf(ctf)

        await interaction.followup.send("Ctf created in the discord server ✅", ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(CTF(bot))
