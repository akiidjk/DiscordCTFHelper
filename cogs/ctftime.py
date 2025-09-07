import os
from datetime import datetime

from discord import (
    CategoryChannel,
    Interaction,
    Member,
    Role,
    TextChannel,
    app_commands,
)
from discord.components import SelectOption
from discord.ext import commands
from discord.ui.select import Select
from discord.ui.view import View

from lib.discord import check_permission, create_channel, create_embed, create_events, create_role, send_error
from lib.logger import logger
from lib.models import CTFModel, ServerModel
from lib.utils import get_ctf_info, sanitize_input

MAX_DESC_LENGTH = 997


class CTF(commands.Cog, name="ctftime"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="init",
        description="Initialize the CTF bot in the discord server.",
    )
    @app_commands.describe(
        category_active="The name of the category for the next or current ctf",
        category_archived="The name of the category for the archived ctf",
        role_manager="The only role that can run the create_ctf command",
        feed_channel="The channel feed for publish the ctf"
    )
    async def init(
        self,
        interaction: Interaction,
        category_active: CategoryChannel,
        category_archived: CategoryChannel,
        role_manager: Role,
        feed_channel: TextChannel,
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

        await self.bot.database.add_server(
            ServerModel(
                id=interaction.guild.id,
                active_category_id=category_active.id,
                archive_category_id=category_archived.id,
                role_manager_id=role_manager.id,
                feed_channel_id=feed_channel.id
            )
        )

        await interaction.followup.send(
            content="Successfully configured the bot! ✅",
            ephemeral=True,
        )

    @app_commands.command(
        name="create",
        description="Create a CTF event in the discord server.",
    )
    @app_commands.describe(
        id="The ID of the event",
        team_name="The name of the team",
    )
    async def create(self, interaction: Interaction, id: int, team_name: str = os.getenv("TEAM_NAME", "")) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        server = await self.bot.database.get_server_by_id(interaction.guild.id)
        if not server:
            await interaction.followup.send(
                "The server is not configured. ❌ Please run the /init command.",
                ephemeral=True,
            )
            return

        if not server.active_category_id or not server.role_manager_id:
            await interaction.followup.send(
                    "Failed to set the category. ❌ Please check the configuration or contact support.",
                    ephemeral=True,
                )
            return

        await check_permission(self,interaction)

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


        role = await create_role(
            interaction=interaction,
            name=data["title"],
        )

        if not role:
            return


        channel = await create_channel(
            interaction=interaction,
            channel_name=data["title"],
            category_id=server.active_category_id,
            role_id=role.id,
        )

        if not channel:
            return

        feed_channel = interaction.guild.get_channel(server.feed_channel_id)

        if not isinstance(feed_channel, TextChannel):
            await interaction.followup.send(
                "The feed channel is not a valid text channel. ❌",
                ephemeral=True,
                )
            return

        msg = await create_embed(
            data=data,
            start_time=start_time,
            end_time=end_time,
            channel=feed_channel,
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

    @app_commands.command(
        name="remove",
        description="Remove a CTF event in the discord server.",
    )
    async def remove(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        await check_permission(self,interaction)

        ctf = await self.bot.database.get_ctfs_list(interaction.guild.id)

        select = Select(
            min_values=1,
            max_values=len(ctf),
            placeholder="Select the CTF to remove",
            options=[
                SelectOption(label=ctf_item.name, value=str(ctf_item.id)) for ctf_item in ctf
            ],
        )

        async def remove(interaction):
            for ctf_id in map(int, select.values):
                ctf_item = await self.bot.database.get_ctf_by_id(ctf_id)
                if not ctf_item:
                    await interaction.followup.send(
                        "Failed to get the information of the CTF. ❌",
                        ephemeral=True,
                    )
                    return

                channel = interaction.guild.get_channel(ctf_item.text_channel_id)
                role = interaction.guild.get_role(ctf_item.role_id)
                event = interaction.guild.get_scheduled_event(ctf_item.event_id)

                if channel:
                    try:
                        await channel.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete the channel: {e}")

                if role:
                    try:
                        await role.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete the role: {e}")

                if event:
                    try:
                        await event.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete the event: {e}")

                try:
                    await self.bot.database.delete_ctf(ctf_id)
                except Exception as e:
                    logger.error(f"Failed to delete the CTF from the database: {e}")
                    await interaction.followup.send(
                        "Failed to delete the CTF from the database. ❌",
                        ephemeral=True,
                    )
                    return
            await interaction.response.send_message("CTF removed successfully ", ephemeral=True)

        select.callback = remove
        view = View()
        view.add_item(select)
        await interaction.followup.send("Select the CTF to remove", view=view, ephemeral=True)

async def setup(bot) -> None:
    await bot.add_cog(CTF(bot))
