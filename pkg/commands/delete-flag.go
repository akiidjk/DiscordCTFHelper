package commands

import (
	"ctfbot"
	"discordutils"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var delete_flag = discord.SlashCommandCreate{
	Name:        "delete-flag",
	Description: "Delete a flag in the ctf.",
}

func DeleteFlagHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("Failed to defer create message", "error", err)
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

		ctf, err := b.Database.GetCTFByChannelID(e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("Failed to fetch ctf by channel id", "error", err)
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
		err = discordutils.CheckPermission(b, e)
		if err != nil {
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "You do not have permission to delete flags. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		report, err := b.Database.GetReport(ctf.ID)
		if err != nil {
			log.Error("Failed to fetch report for ctf", "error", err)
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to fetch report for CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}
		if report != nil && report.Solves > 0 {
			report.Solves -= 1
			err = b.Database.UpdateReport(ctf.ID, *report)
			if err != nil {
				log.Error("Failed to update report for ctf", "error", err)
				_, _ = e.CreateFollowupMessage(discord.MessageCreate{
					Content: "Failed to update report for CTF. ❌",
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
