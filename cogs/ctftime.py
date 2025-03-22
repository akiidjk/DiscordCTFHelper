import os
from datetime import UTC, datetime

from discord import (
    CategoryChannel,
    Color,
    Embed,
    EntityType,
    Interaction,
    Member,
    Message,
    PrivacyLevel,
    Role,
    ScheduledEvent,
    TextChannel,
    app_commands,
)
from discord.errors import HTTPException
from discord.ext import commands

from lib.logger import logger
from lib.models import CTFModel, ServerModel
from lib.utils import check_url, get_ctf_info, get_logo, is_ctfd, sanitize_input

MAX_DESC_LENGTH = 997


class CTF(commands.Cog, name="ctftime"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.category_active_id: dict[int, int] = {}
        self.category_archived_id: dict[int, int] = {}
        self.role_manager_id: dict[int, int] = {}

    async def send_error(self, interaction: Interaction, function: str) -> None:
        await interaction.followup.send(
            f"Failed to get the {function}. ❌",
            ephemeral=True,
        )

    async def create_events(
        self,
        interaction: Interaction,
        info: dict,
        event_description: str,
        start_time: datetime,
        end_time: datetime,
    ) -> ScheduledEvent | None:
        """
        Create a scheduled event in the discord server.

        Args:
            interaction (Interaction): The application command context.
            info (dict): The information of the CTF.
            event_description (str): The description of the event.
            start_time (datetime): The start time of the event.
            end_time (datetime): The end time of the event.

        Returns:
            Optional[ScheduledEvent]: The created scheduled event or None if failed

        """
        guild = interaction.guild

        if guild is None:
            await self.send_error(interaction, "event")
            return None

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
                )

            await interaction.followup.send(
                f"Failed to create the event. ❌\n Error: {e}",
                ephemeral=True,
            )
            return None

        return scheduled_event

    async def set_cat(self, server_id: int) -> bool:
        try:
            server = await self.bot.database.get_server_by_id(server_id)
            logger.debug(f"{server=}")
            if server:
                self.category_active_id[server_id] = server.active_category_id
                self.category_archived_id[server_id] = server.archive_category_id
                self.role_manager_id[server_id] = server.role_manager_id
                return True
        except (HTTPException, AttributeError) as e:
            logger.error(f"Error: {e}")
        return False

    async def create_channel(
        self,
        interaction: Interaction,
        channel_name: str,
        category_id: int,
    ) -> TextChannel | None:
        guild = interaction.guild
        if guild is None:
            await self.send_error(interaction, "channel")
            return None

        category = guild.get_channel(category_id)
        if not isinstance(category, CategoryChannel):
            await self.send_error(interaction, "category")
            return None

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
        else:
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

    async def create_role(self, interaction: Interaction, name: str) -> Role | None:
        if interaction.guild is None:
            return None

        color = Color.random()
        while color == Color.light_gray():
            color = Color.random()

        return await interaction.guild.create_role(
            name=name,
            color=color,
            mentionable=True,
            hoist=True,
        )

    @app_commands.command(
        name="init",
        description="Initialize the CTF bot in the discord server.",
    )
    @app_commands.describe(
        category_active="The name of the category for the next or current ctf",
        category_archived="The name of the category for the archived ctf",
        role_manager="The only role that can run the create_ctf command",
    )
    async def init(
        self,
        interaction: Interaction,
        category_active: CategoryChannel,
        category_archived: CategoryChannel,
        role_manager: Role,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not isinstance(interaction.user, Member) or not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(
                "You need to be the admin of the server to run this command. ❌",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await self.send_error(interaction, "guild")
            return

        if await self.bot.database.get_server_by_id(interaction.guild.id):
            await self.bot.database.delete_server(interaction.guild.id)

        self.category_active_id[interaction.guild.id] = category_active.id
        self.category_archived_id[interaction.guild.id] = category_archived.id
        self.role_manager_id[interaction.guild.id] = role_manager.id

        logger.debug(f"{role_manager=}")

        await self.bot.database.add_server(
            ServerModel(
                id=interaction.guild.id,
                active_category_id=category_active.id,
                archive_category_id=category_archived.id,
                role_manager_id=role_manager.id,
            )
        )

        await interaction.followup.send(
            content=f"Successfully set the category for the active CTF to {category_active.name} and the category for the archived CTF to {category_archived.name}! ✅",
            ephemeral=True,
        )

    @app_commands.command(
        name="create_ctf",
        description="Create a CTF event in the discord server.",
    )
    @app_commands.describe(
        url="The URL of the event",
        team_name="The name of the team",
    )
    async def create_ctf(self, interaction: Interaction, url: str, team_name: str = os.getenv("TEAM_NAME", "")) -> None:
        await interaction.response.defer(ephemeral=True)
        ctfd = is_ctfd(url)

        if ctfd and not team_name:
            await interaction.followup.send(
                "Team name is required when using CTFd (setup in the .env file or add the team-name on the command). ❌",
                ephemeral=True,
            )
            return

        if interaction.guild.id not in self.category_active_id:
            res = await self.set_cat(server_id=interaction.guild.id if interaction.guild else 0)
            if not res:
                await interaction.followup.send(
                    "Failed to set the category the server is not configure. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        if not self.category_active_id[interaction.guild.id] or not self.role_manager_id[interaction.guild.id]:
            res = await self.set_cat(server_id=interaction.guild.id if interaction.guild else 0)
            if not res:
                await interaction.followup.send(
                    "Failed to set the category. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        if not interaction.guild:
            await self.send_error(interaction, "guild")
            return

        role_manager = interaction.guild.get_role(self.role_manager_id[interaction.guild.id])
        if not isinstance(interaction.user, Member) or not role_manager or role_manager not in interaction.user.roles:
            await interaction.followup.send(
                "You don't have the required role to run this command. ❌",
                ephemeral=True,
            )
            return

        if not check_url(url):
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

        channel = await self.create_channel(
            interaction=interaction,
            channel_name=data["title"],
            category_id=self.category_active_id[interaction.guild.id],
        )

        if not channel:
            return

        msg = await self.create_embed(
            data=data,
            start_time=start_time,
            end_time=end_time,
            channel=channel,
        )

        description = str(data["description"])[:MAX_DESC_LENGTH] + "..." if len(data["description"]) >= MAX_DESC_LENGTH else data["description"]

        events = await self.create_events(
            interaction=interaction,
            info=data,
            event_description=description,
            start_time=start_time,
            end_time=end_time,
        )

        if not events:
            return

        role = await self.create_role(
            interaction=interaction,
            name=data["title"],
        )

        if not role:
            return

        ctf = CTFModel(
            id=-1,
            server_id=interaction.guild.id,
            name=data["title"],
            description=data["description"],
            text_channel_id=channel.id,
            event_id=events.id,
            role_id=role.id,
            msg_id=msg.id,
            ctftime_url=url,
            ctfd=ctfd,
            team_name=team_name,
        )

        await self.bot.database.add_ctf(ctf)
        await interaction.followup.send("CTF created in the discord server ✅", ephemeral=True)

    @app_commands.command(
        name="generate_report",
        description="Get a report of a CTF event in the discord server.",
    )
    async def generate_report(self, interaction: Interaction) -> None:
        reports = await self.bot.database.get_reports()
        if not reports:
            await interaction.response.send_message("CTF report not found, this is an error or the ctf is not finished ❗", ephemeral=True)
            return

        total_solves = sum(report.solves for report in reports)
        total_score = sum(report.score for report in reports)
        average_place = sum(report.place for report in reports) / len(reports)

        embed = Embed(title="CTF Report", description="Report of the CTF event", color=Color.blue())
        embed.add_field(name="Average Place", value=average_place, inline=False)
        embed.add_field(name="Total Challenge Solved", value=total_solves, inline=False)
        embed.add_field(name="Total Score", value=total_score, inline=False)

        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=embed, content="CTF report generated in the discord server ✅", ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(CTF(bot))
