package commands

import (
	"database"
	"discordutils"
	"models"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var deleteCreds = discord.SlashCommandCreate{
	Name:        "delete-creds",
	Description: "Delete the creds for the ctf.",
}

func DeleteCredsHandler() handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		db := database.GetInstance().Connection()
		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("failed to defer create message", "error", err)
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

		if err := discordutils.CheckPermission(e); err != nil {
			return err
		}

		// Find the CTF associated with the current channel
		var ctf models.CTFModel
		err := ctf.GetCTFByChannelID(db, e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("failed to fetch CTF for channel", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "failed to find the CTF for this channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}
		if ctf == (models.CTFModel{}) {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No CTFs are currently active in this channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		var creds models.CredsModel
		err = creds.GetCredsByCTFID(db, ctf.ID)
		if err != nil {
			log.Error("failed to fetch creds for CTF", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "failed to retrieve credentials for this CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		if creds == (models.CredsModel{}) {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No credentials are available for this CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		err = creds.DeleteCreds(db)
		if err == nil {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Credential removed correctly ✅",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		} else {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "failed to remove the credentials ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}
	}
}
