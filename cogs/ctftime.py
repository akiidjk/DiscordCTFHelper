import os
from datetime import datetime

from discord import (
    CategoryChannel,
    Interaction,
    Member,
    Role,
    app_commands,
)
from discord.ext import commands

from lib.discord import create_channel, create_embed, create_events, create_role, send_error, set_cat
from lib.logger import logger
from lib.models import CTFModel, ServerModel
from lib.utils import get_ctf_info, sanitize_input

MAX_DESC_LENGTH = 997


class CTF(commands.Cog, name="ctftime"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.category_active_id: dict[int, int] = {}
        self.category_archived_id: dict[int, int] = {}
        self.role_manager_id: dict[int, int] = {}

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
            await send_error(interaction, "guild")
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
        id="The ID of the event",
        team_name="The name of the team",
    )
    async def create_ctf(self, interaction: Interaction, id: int, team_name: str = os.getenv("TEAM_NAME", "")) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        if interaction.guild.id not in self.category_active_id:
            res = await set_cat(self,server_id=interaction.guild.id if interaction.guild else 0)
            if not res:
                await interaction.followup.send(
                    "Failed to set the category the server is not configure. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        if not self.category_active_id[interaction.guild.id] or not self.role_manager_id[interaction.guild.id]:
            res = await set_cat(self,server_id=interaction.guild.id if interaction.guild else 0)
            if not res:
                await interaction.followup.send(
                    "Failed to set the category. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
                return

        role_manager = interaction.guild.get_role(self.role_manager_id[interaction.guild.id])
        if not isinstance(interaction.user, Member) or not role_manager or role_manager not in interaction.user.roles:
            await interaction.followup.send(
                "You don't have the required role to run this command. ❌",
                ephemeral=True,
            )
            return

        data = await get_ctf_info(id)
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

        channel = await create_channel(
            interaction=interaction,
            channel_name=data["title"],
            category_id=self.category_active_id[interaction.guild.id],
        )

        if not channel:
            return

        msg = await create_embed(
            data=data,
            start_time=start_time,
            end_time=end_time,
            channel=channel,
        )

        description = str(data["description"])[:MAX_DESC_LENGTH] + "..." if len(data["description"]) >= MAX_DESC_LENGTH else data["description"]

        events = await create_events(
            self,
            interaction=interaction,
            info=data,
            event_description=description,
            start_time=start_time,
            end_time=end_time,
        )

        if not events:
            return

        role = await create_role(
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
            ctftime_id=id,
            team_name=team_name,
        )

        await self.bot.database.add_ctf(ctf)
        await interaction.followup.send("CTF created in the discord server ✅", ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(CTF(bot))
