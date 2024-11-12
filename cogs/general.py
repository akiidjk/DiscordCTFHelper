"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.2.0
"""

import platform

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


class FeedbackForm(discord.ui.Modal, title="Feeedback"):
    feedback = discord.ui.TextInput(
        label="What do you think about this bot?",
        style=discord.TextStyle.long,
        placeholder="Type your answer here...",
        required=True,
        max_length=256,
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.answer = str(self.feedback)
        self.stop()


class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.prefix = "/"

    @app_commands.command(name="help", description="List all commands the bot has loaded.")
    async def help(self, context: Context) -> None:
        prefix = self.prefix
        embed = discord.Embed(title="Help", description="List of available commands:", color=0xBEBEFE)
        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() == "owner" and not (await self.bot.is_owner(context.author)):
                continue

            commands_list = []
            for command in cog.get_commands():
                if command.hidden:
                    continue
                description = command.description.partition("\n")[0] or "No description"
                if isinstance(command, app_commands.Command):
                    commands_list.append(f"/{command.name} - {description}")
                else:
                    commands_list.append(f"{prefix}{command.name} - {description}")

            if commands_list:
                help_text = "\n".join(commands_list)
                embed.add_field(
                    name=cog_name.capitalize(),
                    value=f"```{help_text}```",
                    inline=False,
                )

        await context.send(embed=embed)

    @app_commands.command(
        name="botinfo",
        description="Get some useful (or not) information about the bot.",
    )
    async def botinfo(self, interaction: discord.Interaction) -> None:
        """
        Get some useful (or not) information about the bot.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            description="Used [Krypton's](https://krypton.ninja) template",
            color=0xBEBEFE,
        )
        embed.set_author(name="Bot Information")
        embed.add_field(name="Owner:", value="Krypton#7331", inline=True)
        embed.add_field(name="Python Version:", value=f"{platform.python_version()}", inline=True)
        embed.add_field(
            name="Prefix:",
            value=f"/ (Slash Commands) or {self.prefix} for normal commands",
            inline=False,
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="serverinfo",
        description="Get some useful (or not) information about the server.",
    )
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        """
        Get some useful (or not) information about the server.

        :param context: The hybrid command context.
        """
        roles = [role.name for role in interaction.guild.roles]
        num_roles = len(roles)
        max_roles = 50
        if num_roles > max_roles:
            roles = roles[:max_roles]
            roles.append(f">>>> Displaying [50/{num_roles}] Roles")
        roles = ", ".join(roles)

        embed = discord.Embed(title="**Server Name:**", description=f"{interaction.guild}", color=0xBEBEFE)
        if interaction.guild.icon is not None:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.add_field(name="Server ID", value=interaction.guild.id)
        embed.add_field(name="Member Count", value=interaction.guild.member_count)
        embed.add_field(name="Text/Voice Channels", value=f"{len(interaction.guild.channels)}")
        embed.add_field(name=f"Roles ({len(interaction.guild.roles)})", value=roles)
        embed.set_footer(text=f"Created at: {interaction.guild.created_at}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="ping",
        description="Check if the bot is alive.",
    )
    async def ping(self, interaction: discord.Interaction) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"The bot latency is {round(self.bot.latency * 1000)}ms.",
            color=0xBEBEFE,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="feedback", description="Submit a feedback for the owners of the bot")
    async def feedback(self, interaction: discord.Interaction) -> None:
        """
        Submit a feedback for the owners of the bot.

        :param context: The hybrid command context.
        """
        feedback_form = FeedbackForm()
        await interaction.response.send_modal(feedback_form)

        await feedback_form.wait()
        interaction = feedback_form.interaction
        await interaction.response.send_message(
            embed=discord.Embed(
                description="Thank you for your feedback, the owners have been notified about it.",
                color=0xBEBEFE,
            )
        )

        app_owner = (await self.bot.application_info()).owner
        await app_owner.send(
            embed=discord.Embed(
                title="New Feedback",
                description=f"{interaction.user} (<@{interaction.user.id}>) has submitted a new feedback:\n```\n{feedback_form.answer}\n```",
                color=0xBEBEFE,
            )
        )


async def setup(bot) -> None:
    await bot.add_cog(General(bot))
