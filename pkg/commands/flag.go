package commands

import (
	"ctfbot"
	"database"
	"fmt"

	"github.com/charmbracelet/log"
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
		client := e.Client()

		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("Failed to defer create message", "error", err)
			return err
		}

		if e.GuildID() == nil {
			log.Warn("Create command used outside of a guild", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used inside a guild. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		options := e.SlashCommandInteractionData()
		flag := options.String("flag")
		mate, okMate := options.OptMember("mate")
		challengeName, okChallenge := options.OptString("challenge_name")

		ctf, err := b.Database.GetCTFByChannelID(e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("Failed to fetch ctf by channel id", "error", err)
			return err
		}

		report, err := b.Database.GetReport(ctf.ID)
		if err != nil {
			log.Error("Failed to fetch report for ctf", "error", err)
			return err
		}

		if report == nil {
			b.Database.AddReport(
				database.ReportModel{
					CTFID:  ctf.ID,
					Place:  -1,
					Score:  -1,
					Solves: 1,
				},
			)
		} else {
			report.Solves += 1
			b.Database.UpdateReport(ctf.ID, *report)
		}

		content := fmt.Sprintf("<@&%s> NEW FLAG FOUND BY %s", ctf.RoleID, e.User().Mention())
		if okMate {
			content += "and " + mate.User.Mention()
		}
		if okChallenge {
			content += " for challenge: " + challengeName
		}

		content += fmt.Sprintf("🎉\n> `%s`", flag)

		msg, err := client.Rest.CreateMessage(e.Channel().ID(), discord.MessageCreate{
			Content: content,
		})
		if err != nil {
			log.Error("Failed to send flag message", "error", err)
			return err
		}

		err = client.Rest.AddReaction(e.Channel().ID(), msg.ID, "🔥")
		if err != nil {
			log.Error("Failed to add reaction to flag message", "error", err)
			return err
		}

		_, err = e.CreateFollowupMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Flag registered successfully! ✅\nTotal solves for this CTF: %d", report.Solves),
			Flags:   discord.MessageFlagEphemeral,
		})
		return err
	}
}
