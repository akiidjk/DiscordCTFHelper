package commands

import (
	"ctfbot"
	"database"
	"discordutils"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var delete_creds = discord.SlashCommandCreate{
	Name:        "delete-creds",
	Description: "Delete the creds for the ctf.",
}

func DeleteCredsHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("Failed to defer create message", "error", err)
			return err
		}

		if e.GuildID() == nil {
			log.Warn("Delete-creds command used outside of a guild", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used inside a guild. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		if err := discordutils.CheckPermission(b, e); err != nil {
			return err
		}

		// Find the CTF associated with the current channel
		ctf, err := b.Database.GetCTFByChannelID(e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("Failed to fetch CTF for channel", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to find the CTF for this channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}
		if ctf == nil {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No CTFs are currently active in this channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		creds, err := b.Database.GetCreds(ctf.ID)
		if err != nil {
			log.Error("Failed to fetch creds for CTF", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to retrieve credentials for this CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		if creds == (database.CredsModel{}) {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No credentials are available for this CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		ok := b.Database.DeleteCreds(ctf.ID)
		if ok {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Credential removed correctly ✅",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		} else {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to remove the credentials ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}
	}
}
