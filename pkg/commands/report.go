package commands

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	ctfbot "ctfhelper/pkg/bot"
	"ctfhelper/pkg/ctftime"

	utils "ctfhelper/pkg/discord"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var report = discord.SlashCommandCreate{
	Name:        "report",
	Description: "Generate a report for the current CTF.",
}

func ReportHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("Failed to defer create message", "error", err)
			return err
		}

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

		if err := utils.CheckPermission(b, e); err != nil {
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
				Content: "No CTF is associated with this channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		report, err := b.Database.GetReport(ctf.ID)
		log.Debug("Fetched report from database", "report", report)
		if err != nil {
			log.Error("Failed to fetch report", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to retrieve the report. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		nameParts := strings.Split(ctf.Name, "-")
		yearStr := strings.TrimSpace(nameParts[len(nameParts)-1])
		year, err := strconv.Atoi(yearStr)
		if err != nil {
			log.Error("Failed to parse year from CTF name", "error", err)
			year = time.Now().Year()
		}

		// If report data is missing, fetch from CTFTime
		// Check if the report was updated in the last day
		var isRecent bool = false
		if report != nil {
			if time.Since(report.LastUpdate) < 24*time.Hour {
				isRecent = true
			}
		}
		if report == nil || report.Place == -1 || report.Score == -1 || !isRecent {
			log.Debug("Fetching from CTFTime", "ctf_id", ctf.ID)
			results, err := ctftime.GetResultsInfo(ctf.CTFTimeID, year, server.TeamID)
			if err != nil {
				log.Error("Failed to fetch results from CTFTime", "error", err)
				_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
					Content: "Failed to retrieve the report from CTFTime. ❌",
					Flags:   discord.MessageFlagEphemeral,
				})
				if sendErr != nil {
					log.Error("Failed to send followup", "error", sendErr)
					return sendErr
				}
				return nil
			}
			if results != nil {
				report = results
				err = b.Database.UpdateReport(ctf.ID, *report)
				if err != nil {
					log.Error("Failed to update report in database", "error", err)
				}
			}
		}

		embed := discord.Embed{
			Title: fmt.Sprintf("Report for %s", ctf.Name),
			Color: utils.ColorBlurple,
			Fields: []discord.EmbedField{
				{
					Name: "Place",
					Value: func() string {
						if report.Place == -1 {
							return "N/A"
						}
						return strconv.Itoa(report.Place)
					}(),
				},
				{
					Name: "Score",
					Value: func() string {
						if report.Place == -1 {
							return "N/A"
						}
						return strconv.Itoa(report.Score)
					}(),
				},
				{
					Name:  "Solves",
					Value: fmt.Sprintf("%d", report.Solves),
				},
			},
			Timestamp: &time.Time{},
		}

		_, err = e.CreateFollowupMessage(discord.MessageCreate{
			Embeds: []discord.Embed{embed},
			Flags:  discord.MessageFlagEphemeral,
		})
		return err
	}
}
