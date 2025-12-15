package commands

import (
	"fmt"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var report = discord.SlashCommandCreate{
	Name:        "report",
	Description: "Generate a report for the current CTF.",
}

func ReportHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		return e.CreateMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Version: %s\nCommit: %s", b.Version, b.Commit),
		})
	}
}
