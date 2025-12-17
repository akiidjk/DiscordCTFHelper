package commands

import (
	"ctfhelper/pkg/database"
	utils "ctfhelper/pkg/discord"
	"discordutils"
	"fmt"
	"log/slog"
	"time"

	ctfbot "ctfhelper/pkg/bot"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var creds = discord.SlashCommandCreate{
	Name:        "creds",
	Description: "Setup creds for the ctf.",
}

func CredsHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		if e.GuildID() == nil {
			log.Warn("Report command used outside of a guild", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used inside a guild. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		server, err := b.Database.GetServerByID(*e.GuildID())
		if err != nil {
			log.Error("Failed to fetch server configuration", "error", err)
			return err
		}

		if server == nil {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "The server is not configured. ❌ Please run the /init command.",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		if err := discordutils.CheckPermission(b, e); err != nil {
			return err
		}

		ctf, err := b.Database.GetCTFByChannelID(e.Channel().ID(), *e.GuildID())
		if err != nil {
			log.Error("Failed to fetch CTF by channel ID", "error", err)
			return err
		}

		if ctf == nil {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "No CTF is associated with this channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		creds, err := b.Database.GetCreds(ctf.ID)
		if err != nil {
			log.Error("Failed to fetch creds by CTF ID", "error", err)
			return err
		}

		// If no creds, show modal to create creds
		if creds == (database.CredsModel{}) {
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
				log.Error("Failed to defer create message", "error", err)
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
