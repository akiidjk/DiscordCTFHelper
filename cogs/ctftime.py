from datetime import datetime
from pprint import pprint

from discord import (
    CategoryChannel,
    Color,
    Embed,
    Interaction,
    Member,
    Role,
    TextChannel,
    app_commands,
    ui,
)
from discord.components import SelectOption
from discord.ext import commands
from discord.ui.select import Select
from discord.ui.view import View

from lib.database import DatabaseManager
from lib.discord import check_permission, create_channel, create_embed, create_events, create_role, send_error
from lib.logger import logger
from lib.models import CTFModel, ReportModel, ServerModel
from lib.utils import get_ctf_info, get_ctfs, get_results_info, sanitize_input

MAX_DESC_LENGTH = 997


class FormCreds(ui.Modal, title='Credentials Form'):
    def __init__(self, db: DatabaseManager, ctf_id: int):
        super().__init__()
        self.db = db
        self.ctf_id = ctf_id

        self.username = ui.TextInput(label="Username", placeholder="Enter the username", required=True, max_length=256)
        self.password = ui.TextInput(label="Password", placeholder="Enter the password", required=True)
        self.personal = ui.TextInput(label="Need personal account", placeholder="yes/no", required=True, max_length=3)

        self.add_item(self.username)
        self.add_item(self.password)
        self.add_item(self.personal)

    async def on_submit(self, interaction: Interaction) -> None:
        await self.db.add_creds(
            ctf_id=self.ctf_id,
            username=self.username.value,
            password=self.password.value,
            personal=(self.personal.value == "yes")
        )
        await interaction.response.send_message(f'Thank you for submitting the credentials, {interaction.user.name}!', ephemeral=True)


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
        feed_channel="The channel feed for publish the ctf",
        team_id="The id of the team",
    )
    async def init(
        self,
        interaction: Interaction,
        category_active: CategoryChannel,
        category_archived: CategoryChannel,
        role_manager: Role,
        feed_channel: TextChannel,
        team_id: int,
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
                feed_channel_id=feed_channel.id,
                team_id=team_id
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
        ctftime_id="The ID of the event",
    )
    async def create(self, interaction: Interaction, ctftime_id: int) -> None:
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

        data = await get_ctf_info(ctftime_id)
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
            manager_id=server.role_manager_id,
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
            ctftime_id=ctftime_id,
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

                server = await self.bot.database.get_server_by_id(interaction.guild.id)
                if not server:
                    await interaction.followup.send(
                        "The server is not configured. ❌ Please run the /init command.",
                        ephemeral=True,
                    )
                    return


                channel = interaction.guild.get_channel(ctf_item.text_channel_id)
                role = interaction.guild.get_role(ctf_item.role_id)
                event = interaction.guild.get_scheduled_event(ctf_item.event_id)
                feedChannel = interaction.guild.get_channel(server.feed_channel_id)

                if feedChannel and isinstance(feedChannel, TextChannel):
                    try:
                        msg = await feedChannel.fetch_message(ctf_item.msg_id)
                        if msg:
                            await msg.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete the message: {e}")

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


    @app_commands.command(
        name="flag",
        description="Register a flag in the ctf.",
    )
    @app_commands.describe(
        flag="the flag",
        challenge_name="the challenge name (optional)"
    )
    async def flag(self, interaction: Interaction, flag: str, challenge_name: str = "") -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        if not isinstance(interaction.user, Member):
            await send_error(interaction, "member")
            return

        ctf = await self.bot.database.get_ctf_by_channel_id(interaction.channel_id, interaction.guild.id)
        if not ctf:
            await interaction.followup.send(
                "No CTFs are currently active in channel. ❌",
                ephemeral=True,
            )
            return

        report = await self.bot.database.get_report(ctf.id)

        if report:
            await self.bot.database.update_report(ctf.id,ReportModel(
                ctf_id=ctf.id,
                place=report.place,
                score=report.score,
                solves= report.solves + 1
            ))
        else:
            await self.bot.database.add_report(ReportModel(
                ctf_id=ctf.id,
                place=-1,
                score=-1,
                solves=1
            ))

        if isinstance(interaction.channel, TextChannel):
            if challenge_name:
                msg = await interaction.channel.send(f"<@&{ctf.role_id}> NEW FLAG FOUND by {interaction.user.mention}! for `{challenge_name}` 🎉\n> `{flag}`")
            else:
                msg = await interaction.channel.send(f"<@&{ctf.role_id}> NEW FLAG FOUND by {interaction.user.mention}! 🎉\n> `{flag}`")
            await msg.add_reaction("🔥")
        else:
            await interaction.followup.send(
                "Unable to register the flag in this channel type. ❌",
                        ephemeral=True,
            )

        await interaction.followup.send("Flag registered successfully ✅", ephemeral=True)


    @app_commands.command(
        name="delete-flag",
        description="Delete a flag in the ctf.",
    )
    async def delete_flag(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        if not isinstance(interaction.user, Member):
            await send_error(interaction, "member")
            return

        ctf = await self.bot.database.get_ctf_by_channel_id(interaction.channel_id, interaction.guild.id)
        if not ctf:
            await interaction.followup.send(
                "No CTFs are currently active in channel. ❌",
                ephemeral=True,
            )
            return

        await check_permission(self,interaction)

        if isinstance(interaction.channel, TextChannel):
            try:
                report = await self.bot.database.get_report(ctf.id)
                if report and report.solves > 0:
                    await self.bot.database.update_report(ctf.id,ReportModel(
                        ctf_id=ctf.id,
                        place=report.place,
                        score=report.score,
                        solves= report.solves - 1
                    ))
                await interaction.followup.send("Flag deleted successfully ✅", ephemeral=True)
            except Exception as e:
                logger.error(f"Failed to delete the message: {e}")
                await interaction.followup.send("Failed to delete the message ❌", ephemeral=True)
        else:
            await interaction.followup.send(
                "Unable to delete the flag in this channel type. ❌",
                        ephemeral=True,
            )

    @app_commands.command(
        name="report",
        description="Generate a report for the current CTF.",
    )
    async def generate_report(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        if not isinstance(interaction.user, Member):
            await send_error(interaction, "member")
            return

        ctf = await self.bot.database.get_ctf_by_channel_id(interaction.channel_id, interaction.guild.id)
        if not ctf:
            await interaction.followup.send(
                "No CTFs are currently active in this channel. ❌",
                ephemeral=True,
            )
            return

        server = await self.bot.database.get_server_by_id(interaction.guild.id)

        report = await self.bot.database.get_report(ctf.id)
        if not report:
            await interaction.followup.send(
                "No report data is available for this CTF. ❌",
                ephemeral=True,
            )
            return

        if report.place == -1 or report.score == -1:
            results = await get_results_info(ctf.ctftime_id,ctf.name.split("-")[-1].strip(), server.team_id)
            if results:
                report = ReportModel(
                    ctf_id=ctf.id,
                    place=results.get("place", -1),
                    score=results.get("points", -1),
                    solves=report.solves
                )
                await self.bot.database.update_report(ctf.id, report)

        embed = Embed(
            title=f"Report for {ctf.name}",
            color=Color.blue(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Place", value=report.place if report.place != -1 else "N/A", inline=False)
        embed.add_field(name="Score", value=report.score, inline=False)
        embed.add_field(name="Solves", value=report.solves, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)




    @app_commands.command(
        name="creds",
        description="Setup creds for the ctf",
    )
    async def creds(self, interaction: Interaction) -> None:
        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        if not isinstance(interaction.user, Member):
            await send_error(interaction, "member")
            return

        ctf = await self.bot.database.get_ctf_by_channel_id(interaction.channel_id, interaction.guild.id)
        if not ctf:
            await interaction.response.send_message(
                "No CTFs are currently active in this channel. ❌",
                ephemeral=True,
            )
            return

        creds = await self.bot.database.get_creds(ctf.id)
        if not creds:
            await interaction.response.send_modal(FormCreds(self.bot.database, ctf.id))
        else:
            description = ""
            for cred in creds:
                description += f"**Username:** `{cred.username}`\n**Password:** `{cred.password}`\n**Need personal:** {'Yes' if cred.personal else '*No*'}\n\n"

            embed = Embed(
                title=f"Credentials for {ctf.name}",
                description=description,
                color=Color.green(),
                timestamp=datetime.now(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="delete-creds",
        description="Delete the creds for the ctf",
    )
    async def delete_creds(self, interaction: Interaction) -> None:
        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        if not isinstance(interaction.user, Member):
            await send_error(interaction, "member")
            return

        ctf = await self.bot.database.get_ctf_by_channel_id(interaction.channel_id, interaction.guild.id)
        if not ctf:
            await interaction.response.send_message(
                "No CTFs are currently active in this channel. ❌",
                ephemeral=True,
            )
            return


        creds = await self.bot.database.get_creds(ctf.id)
        if not creds:
            await interaction.response.send_message(
                "No credentials are available for this CTF. ❌",
                ephemeral=True,
            )
            return

        if(await self.bot.database.delete_creds(ctf.id)):
            await interaction.response.send_message("Credential removed correctly ✅", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to remove the credentials ❌", ephemeral=True)

        return

    @app_commands.command(
        name="next-ctfs",
        description="List the next ctfs on ctftime.",
    )
    @app_commands.describe(
        ephemeral="Whether the response should be ephemeral or not (default: True)",
        limit="The maximum number of CTFs to display (default: 100, max:100)"
    )
    async def next_ctf(self, interaction: Interaction, ephemeral: bool = True, limit: int = 5) -> None:
        await interaction.response.defer(ephemeral=ephemeral)

        if not interaction.guild:
            await send_error(interaction, "guild")
            return

        data_list = await get_ctfs()
        if not data_list or len(data_list) == 0:
            await interaction.followup.send("No CTFs found.", ephemeral=True)
            return

        if limit < 1 or limit > 10:
            limit = 5

        # Build a list of CTFs with required fields
        lines = []
        logger.debug(f"Preparing to list up to {limit} CTFs")
        logger.debug(f"Data list length: {len(data_list)}")
        for idx, ctf in enumerate(data_list[:limit], 1):
            ctf_id = ctf.get("id", "N/A")
            title = ctf.get("title", "N/A")
            start_raw = ctf.get("start", None)
            if start_raw:
                try:
                    start_dt = datetime.fromisoformat(start_raw)
                    # Discord timestamp format: <t:unix[:style]>
                    # We'll use <t:TIMESTAMP:f> for full date/time, and <t:TIMESTAMP:R> for relative
                    start = f"<t:{int(start_dt.timestamp())}:F> (<t:{int(start_dt.timestamp())}:R>)"
                except Exception:
                    start = str(start_raw)
            else:
                start = "N/A"
            ctftime_url = ctf.get("ctftime_url", "N/A")
            duration = ctf.get("duration", {})
            duration_str = f"{duration.get('days', 0)}d {duration.get('hours', 0)}h"
            weight = ctf.get("weight", "N/A")
            onsite = "🏢 Onsite" if ctf.get("onsite", False) else "🌐 Online"
            format_type = ctf.get("format", "N/A")

            # Emoji per il formato
            format_emoji = {
                "Jeopardy": "🎯",
                "Attack-Defense": "⚔️",
                "Mixed": "🔀"
            }.get(format_type, "📋")

            # Link formattato
            link = f"[CTFtime]({ctftime_url})" if ctftime_url != "N/A" else "N/A"

            lines.append(
                f"### {idx} • {title}\n"
                f"🆔 `{ctf_id}` • ⚖️ **Weight:** `{weight}` • 📍 **Location:** {onsite}\n"
                f"📅 **Start:** {start} • ⏱️ **Duration:** `{duration_str}`\n"
                f"{format_emoji} **Format:** {format_type} • 🔗 **Link:** {link}\n"
            )

        embed = Embed(
            title="📋 Next CTFs",
            description="\n".join(lines),
            color=Color.blue(),
            timestamp=datetime.now(),
        )
        embed.set_footer(text=f"Totale: {len(data_list)} CTF disponibili")

        await interaction.followup.send(embed=embed, ephemeral=ephemeral)

async def setup(bot) -> None:
    await bot.add_cog(CTF(bot))
