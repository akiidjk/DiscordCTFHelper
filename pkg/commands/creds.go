package commands

import (
	"fmt"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var creds = discord.SlashCommandCreate{
	Name:        "creds",
	Description: "Setup creds for the ctf.",
}

func CredsHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		return e.CreateMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Version: %s\nCommit: %s", b.Version, b.Commit),
		})
	}
}
