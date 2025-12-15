package commands

import (
	"fmt"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var next_ctfs = discord.SlashCommandCreate{
	Name:        "next-ctfs",
	Description: "List the next ctfs on ctftime.",
	Options: []discord.ApplicationCommandOption{
		discord.ApplicationCommandOptionBool{
			Name:        "ephemeral",
			Description: "Whether the response should be ephemeral or not (default: True)",
		},
		discord.ApplicationCommandOptionBool{
			Name:        "limit",
			Description: "The maximum number of CTFs to display (default: 5, max:10)",
		},
	},
}

func NextCTFsHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		return e.CreateMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Version: %s\nCommit: %s", b.Version, b.Commit),
		})
	}
}
