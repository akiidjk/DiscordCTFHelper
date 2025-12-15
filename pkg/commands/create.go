package commands

import (
	"fmt"
	"time"

	ctfbot "ctfhelper/pkg/bot"
	"ctfhelper/pkg/ctftime"
	"ctfhelper/pkg/database"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"

	utils "ctfhelper/pkg/discord"
)

const MAX_DESC_LENGTH = 4096

var create = discord.SlashCommandCreate{
	Name:        "create",
	Description: "Create a CTF event in the discord server.",
	Options: []discord.ApplicationCommandOption{
		discord.ApplicationCommandOptionInt{
			Name:        "ctftime_id",
			Description: "The ID of the ctf on ctftime",
			Required:    true,
		},
	},
}

func CreateHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		client := e.Client()

		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("Failed to defer create message", "error", err)
			return err
		}

		if e.Guild == nil {
			log.Warn("Create command used outside of a guild", "user_id", e.User().ID)
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "This command can only be used inside a guild. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		options := e.SlashCommandInteractionData()
		ctfTimeId := options.Int("ctftime_id")

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

		if server.ActiveCategoryID == 0 || server.RoleManagerID == 0 {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to set the category. ❌ Please check the configuration or contact support.",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		if err := utils.CheckPermission(b, e); err != nil {
			return err
		}

		data, err := ctftime.GetCTFInfo(ctfTimeId)
		if err != nil {
			log.Error("Failed to retrieve CTF information", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to get the information of the CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		log.Debug("Retrieved CTF information", "data", data)
		if data.Start == "" {
			log.Error("Invalid start time from CTF information")
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to get the information of the CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		if data.Finish == "" {
			log.Error("Invalid finish time from CTF information")
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to get the information of the CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		startTime, err := time.Parse(time.RFC3339, data.Start)
		if err != nil {
			log.Error("Failed to parse CTF start time", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to get the information of the CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		endTime, err := time.Parse(time.RFC3339, data.Finish)
		if err != nil {
			log.Error("Failed to parse CTF end time", "error", err)
			_, sendErr := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to get the information of the CTF. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			if sendErr != nil {
				log.Error("Failed to send followup", "error", sendErr)
				return sendErr
			}
			return nil
		}

		title := fmt.Sprintf("%s - %d", data.Title, startTime.Year())

		present, err := b.Database.IsCTFPresent(title, *e.GuildID())
		if err != nil {
			log.Error("Failed to check existing CTF", "error", err)
			return err
		}
		if present {
			_, err := e.CreateFollowupMessage(discord.MessageCreate{
				Content: "The CTF is already present in the discord server. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		log.Info("Creating role and channel for CTF", "title", title)
		role, err := utils.CreateRole(
			b,
			e,
			title,
		)
		if err != nil {
			log.Error("Failed to create role", "error", err)
			return err
		}
		if role == nil {
			return nil
		}

		log.Debug("Created role for CTF", "role_id", role.ID)
		log.Debug("Creating channel for CTF", "title", title)
		channel, err := utils.CreateChannel(
			b,
			e,
			title,
			server.ActiveCategoryID,
			role.ID,
			server.RoleManagerID,
		)
		if err != nil {
			log.Error("Failed to create channel", "error", err)
			return err
		}
		if channel == nil {
			return nil
		}

		log.Debug("Created channel for CTF", "channel_id", (*channel).ID())
		log.Info("Sending welcome message and pinning link", "channel_id", (*channel).ID())
		welcomeContent := fmt.Sprintf("%s Welcome to the CTF **%s**! 🎉", role.Mention(), title)
		if _, err := client.Rest().CreateMessage((*channel).ID(), discord.MessageCreate{
			Content: welcomeContent,
		}); err != nil {
			log.Error("Failed to send welcome message", "error", err)
			return err
		}

		log.Debug("Sending link message and pinning", "channel_id", (*channel).ID())
		linkMessage, err := client.Rest().CreateMessage((*channel).ID(), discord.MessageCreate{
			Content: "Link to ctf: " + data.URL,
		})
		if err != nil {
			log.Error("Failed to send link message", "error", err)
			return err
		}

		if err := client.Rest().PinMessage((*channel).ID(), linkMessage.ID); err != nil {
			log.Error("Failed to pin message", "error", err)
		}

		log.Info("Creating embed and scheduled event for CTF", "title", title)
		feedChannel, err := client.Rest().GetChannel(server.FeedChannelID)
		if err != nil {
			log.Error("Failed to fetch feed channel", "error", err)
			return err
		}

		log.Debug("Fetched feed channel", "channel_id", feedChannel.ID())

		log.Debug("Creating embed message for CTF", "title", title)
		embedMsg, err := utils.CreateEmbed(
			b,
			data,
			startTime,
			endTime,
			feedChannel,
		)
		if err != nil {
			log.Error("Failed to create embed", "error", err)
			return err
		}
		if embedMsg == nil {
			return nil
		}

		var description string
		if len(data.Description) >= MAX_DESC_LENGTH {
			description = data.Description[:MAX_DESC_LENGTH] + "..."
		}

		log.Info("Creating scheduled event for CTF", "title", title)
		events, err := utils.CreateEvents(
			b,
			e,
			data,
			description,
			startTime,
			endTime,
		)
		if err != nil {
			log.Error("Failed to create events", "error", err)
			return err
		}
		if events == (discord.GuildScheduledEvent{}) {
			return nil
		}

		ctf := database.CTFModel{
			ID:            -1,
			ServerID:      *e.GuildID(),
			Name:          title,
			Description:   description,
			TextChannelID: (*channel).ID(),
			EventID:       events.ID,
			RoleID:        role.ID,
			MsgID:         embedMsg.ID,
			CTFTimeID:     int64(ctfTimeId),
		}

		if err := b.Database.AddCTF(ctf); err != nil {
			log.Error("Failed to add CTF to database", "error", err)
			return err
		}

		if teamRole, _ := b.Client.Rest().GetRole(*e.GuildID(), server.RoleTeamID); teamRole != nil {
			interactionChannel := e.ApplicationCommandInteraction.Channel()
			feedMention := fmt.Sprintf("<#%s>", feedChannel.ID().String())
			if _, err := b.Client.Rest().CreateMessage(interactionChannel.ID(), discord.MessageCreate{
				Content: fmt.Sprintf("%s New CTF published in %s 🎉", teamRole.Mention(), feedMention),
			}); err != nil {
				log.Error("Failed to announce CTF to team role", "error", err)
			}
		}

		_, err = e.CreateFollowupMessage(discord.MessageCreate{
			Content: "CTF created in the discord server ✅",
			Flags:   discord.MessageFlagEphemeral,
		})
		return err
	}
}
