package commands

import (
	"fmt"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var vote = discord.SlashCommandCreate{
	Name:        "vote",
	Description: "Vote the next ctf to participate in",
}

func VoteHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		return e.CreateMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Version: %s\nCommit: %s", b.Version, b.Commit),
		})
	}
}
