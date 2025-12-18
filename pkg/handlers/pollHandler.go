package handlers

import (
	"commands"
	"database"
	"models"
	"strconv"
	"strings"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/events"
)

func VotePollHandler() bot.EventListener {
	return bot.NewListenerFunc(func(e *events.MessageCreate) {
		db := database.GetInstance().Connection()
		if e.Message.Type == discord.MessageTypePollResult && e.Message.Author.ID == *e.Message.ApplicationID {
			if e.Message.MessageReference == nil || e.Message.MessageReference.MessageID == nil {
				log.Error("Poll result message does not have a message reference")
				return
			}
			message, err := e.Client().Rest.GetMessage(e.ChannelID, *e.Message.MessageReference.MessageID)
			if err != nil {
				log.Error("failed to fetch original message for poll result", "err", err, "message_id", e.Message.MessageReference.MessageID)
				return
			}
			if message.Poll == nil || message.Poll.Results == nil {
				log.Error("Original message does not contain poll data")
				return
			}

			maxVotes := -1
			maxIndex := -1
			for i, ans := range message.Poll.Results.AnswerCounts {
				if ans.Count > maxVotes {
					maxVotes = ans.Count
					maxIndex = i
				}
			}

			if maxIndex >= 0 && maxIndex < len(message.Poll.Answers) {
				bestAnswer := *message.Poll.Answers[maxIndex].PollMedia.Text
				log.Info("Most voted answer found", "answer", bestAnswer, "votes", maxVotes)
				ctftimeID := strings.TrimSpace(bestAnswer[strings.LastIndex(bestAnswer, "(")+1 : len(bestAnswer)-1])
				log.Info("CTFTime ID estratto", "ctf_time_id", ctftimeID)
				ctfTimeIDInt, err := strconv.Atoi(ctftimeID)
				if err != nil {
					log.Error("Error during CTFTime ID conversion", "err", err, "ctf_time_id", ctftimeID)
					return
				}
				var server models.Server
				err = server.GetByID(db, *e.GuildID)
				if err != nil {
					log.Error("Error fetching server configuration", "err", err, "guild_id", *e.GuildID)
					return
				}

				// trigger the creation of the CTF
				commands.CreateCTF(e.GuildID, e.Client(), ctfTimeIDInt, server)
			} else {
				log.Warn("No answers found in the poll")
			}
		}
	})
}
