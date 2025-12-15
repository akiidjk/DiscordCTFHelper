package commands

import (
	"fmt"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var cinit = discord.SlashCommandCreate{
	Name:        "init",
	Description: "Initialize the CTF bot in the discord server.",
	Options: []discord.ApplicationCommandOption{
		discord.ApplicationCommandOptionChannel{
			Name:        "category_active",
			Description: "The name of the category for the next or current ctf",
			Required:    true,
			ChannelTypes: []discord.ChannelType{
				discord.ChannelTypeGuildCategory,
			},
		},
		discord.ApplicationCommandOptionChannel{
			Name:        "category_archived",
			Description: "The name of the category for the archived ctf",
			Required:    true,
			ChannelTypes: []discord.ChannelType{
				discord.ChannelTypeGuildCategory,
			},
		},
		discord.ApplicationCommandOptionRole{
			Name:        "role_manager",
			Description: "The only role that can run the create_ctf command",
			Required:    true,
		},
		discord.ApplicationCommandOptionChannel{
			Name:        "feed_channel",
			Description: "The channel feed for publish the ctf",
			Required:    true,
			ChannelTypes: []discord.ChannelType{
				discord.ChannelTypeGuildText,
			},
		},
		discord.ApplicationCommandOptionInt{
			Name:        "team_id",
			Description: "The id of the team",
			Required:    true,
		},
		discord.ApplicationCommandOptionRole{
			Name:        "role_team_id",
			Description: "The role id of the team for tagging purposes",
			Required:    true,
		},
	},
}

func InitHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		return e.CreateMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Version: %s\nCommit: %s", b.Version, b.Commit),
		})
	}
}
