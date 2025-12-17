package commands

import (
	"errors"
	"fmt"
	"time"

	ctfbot "ctfhelper/pkg/bot"
	"ctfhelper/pkg/ctftime"
	"ctfhelper/pkg/database"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
	"github.com/disgoorg/snowflake/v2"

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

func CreateCTF(guildId *snowflake.ID, client *bot.Client, channel discord.MessageChannel, b *ctfbot.Bot, ctfTimeId int, server database.ServerModel) error {
	data, err := ctftime.GetCTFInfo(ctfTimeId)
	if err != nil {
		log.Error("Failed to retrieve CTF information", "error", err)
		return errors.New("Failed to get the information of the CTF. ❌")
	}

	log.Debug("Retrieved CTF information", "data", data)
	if data.Start == "" {
		log.Error("Invalid start time from CTF information")
		return errors.New("Failed to get the information of the CTF. ❌")
	}

	if data.Finish == "" {
		log.Error("Invalid finish time from CTF information")
		return errors.New("Failed to get the information of the CTF. ❌")
	}

	startTime, err := time.Parse(time.RFC3339, data.Start)
	if err != nil {
		log.Error("Failed to parse CTF start time", "error", err)
		return errors.New("Failed to get the information of the CTF. ❌")
	}

	endTime, err := time.Parse(time.RFC3339, data.Finish)
	if err != nil {
		log.Error("Failed to parse CTF end time", "error", err)
		return errors.New("Failed to get the information of the CTF. ❌")
	}

	title := fmt.Sprintf("%s - %d", data.Title, startTime.Year())

	present, err := b.Database.IsCTFPresent(title, *guildId)
	if err != nil {
		log.Error("Failed to check existing CTF", "error", err)
		return err
	}
	if present {
		return errors.New("The CTF is already present in the discord server. ❌")
	}

	log.Info("Creating role and channel for CTF", "title", title)
	role, err := utils.CreateRole(
		b,
		guildId,
		title,
	)
	if err != nil {
		log.Error("Failed to create role", "error", err)
		return err
	}
	if role == nil {
		return errors.New("Failed to create role")
	}

	log.Debug("Created role for CTF", "role_id", role.ID)
	log.Debug("Creating channel for CTF", "title", title)
	channelCTF, err := utils.CreateChannel(
		b,
		guildId,
		title,
		server.ActiveCategoryID,
		role.ID,
		server.RoleManagerID,
	)
	if err != nil {
		log.Error("Failed to create channel", "error", err)
		return err
	}
	if channelCTF == nil {
		return errors.New("failed to create channel")
	}

	log.Debug("Created channel for CTF", "channel_id", (*channelCTF).ID())
	log.Info("Sending welcome message and pinning link", "channel_id", (*channelCTF).ID())
	welcomeContent := fmt.Sprintf("%s Welcome to the CTF **%s**! 🎉", role.Mention(), title)
	if _, err := client.Rest.CreateMessage((*channelCTF).ID(), discord.MessageCreate{
		Content: welcomeContent,
	}); err != nil {
		log.Error("Failed to send welcome message", "error", err)
		return err
	}

	log.Debug("Sending link message and pinning", "channel_id", (*channelCTF).ID())
	linkMessage, err := client.Rest.CreateMessage((*channelCTF).ID(), discord.MessageCreate{
		Content: "Link to ctf: " + data.URL,
	})
	if err != nil {
		log.Error("Failed to send link message", "error", err)
		return err
	}

	if err := client.Rest.PinMessage((*channelCTF).ID(), linkMessage.ID); err != nil {
		log.Error("Failed to pin message", "error", err)
	}

	log.Info("Creating embed and scheduled event for CTF", "title", title)
	feedChannel, err := client.Rest.GetChannel(server.FeedChannelID)
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
		return errors.New("failed to create embed message")
	}

	var description string
	if len(data.Description) >= MAX_DESC_LENGTH {
		description = data.Description[:MAX_DESC_LENGTH] + "..."
	}

	log.Info("Creating scheduled event for CTF", "title", title)
	events, err := utils.CreateEvents(
		b,
		guildId,
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
		return errors.New("failed to create scheduled event")
	}

	ctf := database.CTFModel{
		ID:            -1,
		ServerID:      *guildId,
		Name:          title,
		Description:   description,
		TextChannelID: (*channelCTF).ID(),
		EventID:       events.ID,
		RoleID:        role.ID,
		MsgID:         embedMsg.ID,
		CTFTimeID:     int64(ctfTimeId),
	}

	if err := b.Database.AddCTF(ctf); err != nil {
		log.Error("Failed to add CTF to database", "error", err)
		return err
	}

	return nil
}

func CreateHandler(b *ctfbot.Bot) handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
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
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to fetch server configuration. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
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
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "You do not have permission to use this command. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		err = CreateCTF(e.GuildID(), &b.Client, e.Channel(), b, ctfTimeId, *server)
		if err != nil {
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: err.Error(),
				Flags:   discord.MessageFlagEphemeral,
			})
			return nil
		}

		// Fetch the created CTF to confirm and announce
		ctf, err := b.Database.GetCTFByCTFTimeID(int64(ctfTimeId))
		if err != nil {
			log.Error("Failed to fetch CTF after creation", "error", err)
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to fetch CTF after creation. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}
		if ctf == nil {
			log.Error("CTF not found after creation")
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "CTF not found after creation. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return nil
		}

		feedChannel, err := b.Client.Rest.GetChannel(server.FeedChannelID)
		if err != nil {
			log.Error("Failed to fetch feed channel", "error", err)
			_, _ = e.CreateFollowupMessage(discord.MessageCreate{
				Content: "Failed to fetch feed channel. ❌",
				Flags:   discord.MessageFlagEphemeral,
			})
			return err
		}

		if teamRole, _ := b.Client.Rest.GetRole(*e.GuildID(), server.RoleTeamID); teamRole != nil {
			interactionChannel := e.ApplicationCommandInteraction.Channel()
			feedMention := fmt.Sprintf("<#%s>", feedChannel.ID().String())
			if _, err := b.Client.Rest.CreateMessage(interactionChannel.ID(), discord.MessageCreate{
				Content: fmt.Sprintf("%s New CTF published in %s 🎉", teamRole.Mention(), feedMention),
			}); err != nil {
				log.Error("Failed to announce CTF to team role", "error", err)
			}
		}

		_, _ = e.CreateFollowupMessage(discord.MessageCreate{
			Content: "CTF created in the discord server ✅",
			Flags:   discord.MessageFlagEphemeral,
		})
		return nil
	}
}
