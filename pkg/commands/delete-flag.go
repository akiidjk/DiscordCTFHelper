package commands

import (
	"database"
	"discordutils"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var deleteFlag = discord.SlashCommandCreate{
	Name:        "delete-flag",
	Description: "Delete a flag in the ctf.",
}

func DeleteFlagHandler() handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		db := database.GetInstance()
		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("failed to defer create message", "error", err)
			return err
		}

		if e.GuildID() == nil {
			log.Warn("Delete-flag command used outside of a guild", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used inside a guild. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		// Check if user is a guild member
		if e.Member() == nil {
			log.Warn("Delete-flag command used by non-member", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used by a guild member. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		ctf, err := db.GetCTFByChannelID(e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("failed to fetch ctf by channel id", "error", err)
			return err
		}

		if ctf == nil {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No CTFs are currently active in channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		// Permission check placeholder (implement as needed)
		err = discordutils.CheckPermission(e)
		if err != nil {
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "You do not have permission to delete flags. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		report, err := db.GetReport(ctf.ID)
		if err != nil {
			log.Error("failed to fetch report for ctf", "error", err)
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "failed to fetch report for CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}
		if report != nil && report.Solves > 0 {
			report.Solves -= 1
			err = db.UpdateReport(ctf.ID, *report)
			if err != nil {
				log.Error("failed to update report for ctf", "error", err)
				_, _ = e.CreateFollowupMessage(discord.MessageCreate{
					Content: "failed to update report for CTF. ❌",
					Flags:   discord.MessageFlagEphemeral,
				})
				return err
			}
		}
		_, err = e.CreateFollowupMessage(discord.MessageCreate{
			Content: "Flag deleted successfully ✅",
			Flags:   discord.MessageFlagEphemeral,
		})
		return err
	}
}
