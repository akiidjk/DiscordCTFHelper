package commands

import (
	"fmt"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var flag = discord.SlashCommandCreate{
	Name:        "flag",
	Description: "Register a flag in the ctf.",
	Options: []discord.ApplicationCommandOption{
		discord.ApplicationCommandOptionString{
			Name:        "flag",
			Description: "The flag.",
			Required:    true,
		},
		discord.ApplicationCommandOptionUser{
			Name:        "mate",
			Description: "If you solved the challenge together with someone, specify their tag",
			Required:    false,
		},
		discord.ApplicationCommandOptionString{
			Name:        "challenge_name",
			Description: "the challenge name (optional)",
			Required:    false,
		},
	},
}

func FlagHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		return e.CreateMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Version: %s\nCommit: %s", b.Version, b.Commit),
		})
	}
}
