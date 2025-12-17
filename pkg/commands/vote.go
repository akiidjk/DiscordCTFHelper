package commands

import (
	"ctfbot"
	"ctftime"
	"fmt"
	"time"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var vote = discord.SlashCommandCreate{
	Name:        "vote",
	Description: "Vote the next ctf to participate in",
}

func VoteHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		if e.GuildID() == nil {
			log.Warn("Create command used outside of a guild", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used inside a guild. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		ctfs, err := ctftime.GetCTFs()
		if err != nil {
			log.Error("Failed to get CTFs", "error", err)
			return err
		}

		var ctfsThisWeek []ctftime.Event
		now := time.Now()
		year, week := now.ISOWeek()
		for _, ctf := range ctfs {
			startTime, err := time.Parse(time.RFC3339, ctf.Start)
			if err != nil {
				log.Warn("Unable to parse CTF start date", "ctf", ctf.Title, "start", ctf.Start, "error", err)
				continue
			}
			y, w := startTime.ISOWeek()
			if y == year && w == week {
				ctfsThisWeek = append(ctfsThisWeek, ctf)
			}
		}

		if len(ctfsThisWeek) < 2 || len(ctfsThisWeek) > 10 {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "There must be between 2 and 10 CTFs this week to create a vote. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		pollTitle := "Vote the next CTF to participate in! 🎉"
		// emojiName := "🏆"

		log.Info("Creating vote poll", "ctfs_count", len(ctfsThisWeek))

		err = e.CreateMessage(
			discord.MessageCreate{
				Content: "It's time to vote for the next CTF! Cast your vote below: 🗳️",
				Poll: &discord.PollCreate{
					LayoutType:       discord.PollLayoutTypeDefault,
					AllowMultiselect: false,
					Question: discord.PollMedia{
						Text: &pollTitle,
						// Emoji: &discord.PartialEmoji{Name: &emojiName},
					},
					Answers: func() []discord.PollMedia {
						var options []discord.PollMedia

						for _, ctf := range ctfsThisWeek {
							log.Debug("Adding CTF to poll options", "ctf", ctf.Title)
							text := ctf.Title + fmt.Sprintf("(%d)", ctf.CtfID)
							options = append(options, discord.PollMedia{
								Text: &text,
							})
						}
						return options
					}(),
					Duration: 48,
				},
			},
		)

		return err
	}
}
