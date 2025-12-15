package commands

import (
	"fmt"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var create = discord.SlashCommandCreate{
	Name:        "create",
	Description: "Create a CTF event in the discord server.",
	Options: []discord.ApplicationCommandOption{
		discord.ApplicationCommandOptionInt{
			Name:        "ctftime_id",
			Description: "The ID of the ctf on ctftime",
			Required:    true,
		},
	},
}

func CreateHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		return e.CreateMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Version: %s\nCommit: %s", b.Version, b.Commit),
		})
	}
}
