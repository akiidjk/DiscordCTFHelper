package commands

import (
	"database"
	"fmt"
	"models"

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

func FlagHandler() handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		db := database.GetInstance().Connection()
		client := e.Client()

		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("failed to defer create message", "error", err)
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

		var ctf models.CTFModel
		err := ctf.GetCTFByChannelID(db, e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("failed to fetch ctf by channel id", "error", err)
			return err
		}
		if ctf == (models.CTFModel{}) {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No CTFs are currently active in channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		var report models.ReportModel
		err = report.GetReportByCTFID(db, ctf.ID)
		if err != nil {
			log.Error("failed to fetch report for ctf", "error", err)
			return err
		}

		if report == (models.ReportModel{}) {
			report = models.ReportModel{
				CTFID:  ctf.ID,
				Place:  -1,
				Score:  -1,
				Solves: 1,
			}
			report.AddReport(db)
		} else {
			report.Solves += 1
			report.CTFID = ctf.ID
			report.UpdateReport(db)
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
			log.Error("failed to send flag message", "error", err)
			return err
		}

		err = client.Rest.AddReaction(e.Channel().ID(), msg.ID, "🔥")
		if err != nil {
			log.Error("failed to add reaction to flag message", "error", err)
			return err
		}

		_, err = e.CreateFollowupMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Flag registered successfully! ✅\nTotal solves for this CTF: %d", report.Solves),
			Flags:   discord.MessageFlagEphemeral,
		})
		return err
	}
}
