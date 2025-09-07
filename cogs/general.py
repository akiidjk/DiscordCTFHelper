import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Bot


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
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="List all commands the bot has loaded.")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="Help", description="List of available commands:", color=0xBEBEFE)
        if not interaction.message:
            return
        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() == "owner" and not (await self.bot.is_owner(interaction.message.author)):
                continue

            commands_list = []
            for command in cog.get_app_commands():
                description = command.description.partition("\n")[0] or "No description"
                commands_list.append(f"/{command.name} - {description}")

            if commands_list:
                help_text = "\n".join(commands_list)
                embed.add_field(
                    name=cog_name.capitalize(),
                    value=f"```{help_text}```",
                    inline=False,
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="ping",
        description="Check if the bot is alive.",
    )
    async def ping(self, interaction: discord.Interaction) -> None:
        """
        Check if the bot is alive.

        Args:
            interaction (discord.Interaction): The interaction object.

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

        Args:
            interaction (discord.Interaction): The interaction object.

        """
        feedback_form = FeedbackForm()
        await interaction.response.send_modal(feedback_form)

        await feedback_form.wait()
        interaction = feedback_form.interaction
        await interaction.response.send_message(
            embed=discord.Embed(
                description="Thank you for your feedback, the owners have been notified about it.",
                color=0xBEBEFE,
            ),
            ephemeral=True,
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
