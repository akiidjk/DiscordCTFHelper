from datetime import UTC, datetime

from discord import Embed, Member, Message, PermissionOverwrite, ScheduledEvent
from discord.channel import CategoryChannel, TextChannel
from discord.client import HTTPException
from discord.colour import Color
from discord.enums import EntityType, PrivacyLevel
from discord.interactions import Interaction
from discord.role import Role

from lib.logger import logger
from lib.utils import get_logo


async def send_error(interaction: Interaction, function: str) -> None:
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
            self: The instance of the cog.
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
            await send_error(interaction, "event")
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

async def create_channel(
        interaction: Interaction,
        channel_name: str,
        category_id: int,
        role_id: int,
        manager_id: int,
    ) -> TextChannel | None:
        guild = interaction.guild
        if guild is None:
            await send_error(interaction, "channel")
            return None

        category = guild.get_channel(category_id)
        if not isinstance(category, CategoryChannel):
            await send_error(interaction, "category")
            return None

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,

            )
            await channel.edit(sync_permissions=False)

            overwrite = PermissionOverwrite()
            overwrite.view_channel = False
            await channel.set_permissions(guild.default_role,overwrite=overwrite)

            manager = guild.get_role(manager_id)
            if manager is None:
                await send_error(interaction, "manager")
                return None
            overwrite = PermissionOverwrite()
            overwrite.view_channel = False
            await channel.set_permissions(manager,overwrite=overwrite)

            role = guild.get_role(role_id)
            if role is None:
                await send_error(interaction, "role")
                return None
            overwrite = PermissionOverwrite()
            overwrite.view_channel = True
            overwrite.send_messages = True
            await channel.set_permissions(role,overwrite=overwrite)
        except HTTPException as e:
            logger.error(f"Error: {e}")
            await interaction.followup.send(
                f"Failed to create the channel or assign the permission. ❌\n Error: {e}",
                ephemeral=True,
            )
            return None
        else:
            return channel

async def create_embed(data: dict, start_time: datetime, end_time: datetime, channel: TextChannel) -> Message:
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
        # await msg.pin()
        return msg

async def create_role(interaction: Interaction, name: str) -> Role | None:
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


async def check_permission(self,interaction):
    server = await self.bot.database.get_server_by_id(interaction.guild.id)
    role_manager = interaction.guild.get_role(server.role_manager_id)
    if not isinstance(interaction.user, Member) or not role_manager or role_manager not in interaction.user.roles:
        await interaction.followup.send(
            "You don't have the required role to run this command. ❌",
            ephemeral=True,
        )
        return
