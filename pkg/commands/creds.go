package commands

import (
	"database"
	"discordutils"
	"fmt"
	"log/slog"
	"models"
	"time"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var creds = discord.SlashCommandCreate{
	Name:        "creds",
	Description: "Setup creds for the ctf.",
}

func CredsHandler() handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		db := database.GetInstance().Connection()
		if e.GuildID() == nil {
			log.Warn("Report command used outside of a guild", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used inside a guild. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		var server models.ServerModel
		err := server.GetServerByID(db, *e.GuildID())
		if err != nil {
			log.Error("failed to fetch server configuration", "error", err)
			return err
		}

		if server == (models.ServerModel{}) {
			if err := e.DeferCreateMessage(true); err != nil {
				log.Error("failed to defer create message", "error", err)
				return err
			}

			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "The server is not configured. ❌ Please run the /init command.",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		if err := discordutils.CheckPermission(e); err != nil {
			return err
		}

		var ctf models.CTFModel
		err = ctf.GetCTFByChannelID(db, e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("failed to fetch CTF by channel ID", "error", err)
			return err
		}

		if ctf == (models.CTFModel{}) {
			if err := e.DeferCreateMessage(true); err != nil {
				log.Error("failed to defer create message", "error", err)
				return err
			}

			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No CTF is associated with this channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		var creds models.CredsModel
		err = creds.GetCredsByCTFID(db, ctf.ID)
		if err != nil {
			log.Error("failed to fetch creds by CTF ID", "error", err)
			return err
		}

		// If no creds, show modal to create creds
		log.Debug("Fetched creds", "creds", creds)
		if creds == (models.CredsModel{}) {
			log.Info("No creds found for CTF, showing modal", "ctf_id", ctf.ID)
			// Modal
			modal := discord.NewModalCreateBuilder().
				SetTitle("Credentials Form").
				SetCustomID(fmt.Sprintf("creds_modal_%d", ctf.ID)).
				AddLabel("Username", discord.NewTextInput("username",
					discord.TextInputStyleShort).
					WithMinLength(1).
					WithMaxLength(20).
					WithPlaceholder("Enter the username").
					WithRequired(true),
				).AddLabel("Password", discord.NewTextInput("password",
				discord.TextInputStyleShort).
				WithMinLength(1).
				WithMaxLength(100).
				WithPlaceholder("Enter the password").
				WithRequired(true),
			).AddLabel("Personal", discord.NewTextInput("personal",
				discord.TextInputStyleShort).
				WithMinLength(2).
				WithMaxLength(3).
				WithPlaceholder("yes/no").
				WithRequired(true)).Build()

			log.Debug("Creating creds modal", "modal", modal)

			if err := e.Modal(modal); err != nil {
				log.Error("Error creating modal", slog.Any("err", err))
			}

			return nil
		} else {
			// Show creds in an embed
			log.Info("Credentials found for CTF, displaying", "ctf_id", ctf.ID)
			if err := e.DeferCreateMessage(true); err != nil {
				log.Error("failed to defer create message", "error", err)
				return err
			}
			description := fmt.Sprintf("**Username:** `%s`\n**Password:** `%s`\n**Need personal:** ", creds.Username, creds.Password)
			if creds.Personal {
				description += "Yes"
			} else {
				description += "No"
			}
			description += "\n\n"

			now := time.Now()
			embed := discord.Embed{
				Title:       "Credentials for " + ctf.Name,
				Description: description,
				Color:       discordutils.ColorGreen,
				Timestamp:   &now,
			}

			_, err = e.CreateFollowupMessage(discord.MessageCreate{
				Embeds: []discord.Embed{embed},
				Flags:  discord.MessageFlagEphemeral,
			})
			return err
		}
	}
}
