package ctfbot

import (
	"config"
	"context"
	"database"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/log"

	"github.com/disgoorg/disgo"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/cache"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/events"
	"github.com/disgoorg/disgo/gateway"
	"github.com/disgoorg/snowflake/v2"
)

var STATUSES = []string{
	"Setting up your CTF events...",
	"Syncing with CTFTime's latest info...",
	"Retrieving event details from CTFTime...",
	"Preparing for your next CTF event...",
}

func New(cfg config.Config, version string, commit string) *Bot {
	return &Bot{
		Cfg: cfg,
		// Paginator: paginator.New(),
		Version: version,
		Commit:  commit,
	}
}

type Bot struct {
	Cfg    config.Config
	Client bot.Client
	// Paginator *paginator.Manager
	Version  string
	Commit   string
	Database *database.Database
}

func (b *Bot) SetupBot(shouldCleanCommands *bool, listeners ...bot.EventListener) error {
	client, err := disgo.New(b.Cfg.Bot.Token,
		bot.WithGatewayConfigOpts(gateway.WithIntents(gateway.IntentGuilds, gateway.IntentGuildMessages, gateway.IntentMessageContent, gateway.IntentGuildMembers, gateway.IntentGuildMessageReactions, gateway.IntentGuildScheduledEvents)),
		bot.WithCacheConfigOpts(cache.WithCaches(cache.FlagGuilds)),
		// bot.WithEventListeners(b.Paginator),
		bot.WithEventListeners(listeners...),
		bot.WithEventListenerFunc(b.modalListener),
		bot.WithEventListenerFunc(b.selectListener),
		bot.WithEventListenerFunc(b.pollListener),
		bot.WithEventListenerFunc(b.messageListener),
		bot.WithEventListenerFunc(b.reactionAddListener),
		bot.WithEventListenerFunc(b.reactionRemoveListener),
		bot.WithEventListenerFunc(b.scheduledEventUpdateListener),
	)
	if err != nil {
		return err
	}

	if *shouldCleanCommands {
		var id snowflake.ID = 1345702395178651698
		if err := b.resetAllCommands(&id); err != nil {
			log.Error("Failed to reset commands", "err", err)
		}
	}

	b.Client = *client
	return nil
}

func changePresenceStatus(ctx context.Context, client bot.Client) error {
	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()
	for range ticker.C {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		status := STATUSES[time.Now().UnixNano()%int64(len(STATUSES))]
		err := client.SetPresence(
			ctx,
			gateway.WithOnlineStatus(discord.OnlineStatusOnline),
			gateway.WithListeningActivity(status),
		)
		if err != nil {
			log.Error("Failed to change presence status", "err", err)
		}
		cancel()
	}

	return nil
}

// Delete all commands from Discord
func (b *Bot) resetAllCommands(guildID *snowflake.ID) error {
	if guildID != nil {
		// Delete GUILD-SPECIFIC commands
		fmt.Printf("Clearing guild commands for guild %d...\n", *guildID)
		commands, err := b.Client.Rest.GetGuildCommands(b.Client.ApplicationID, *guildID, false)
		if err != nil {
			return err
		}

		for _, cmd := range commands {
			if err := b.Client.Rest.DeleteGuildCommand(b.Client.ApplicationID, *guildID, cmd.ID()); err != nil {
				log.Printf("Error deleting guild command %s: %v\n", cmd.Name, err)
			} else {
				fmt.Printf("✓ Deleted guild command: %s\n", cmd.Name())
			}
		}
	}
	// Delete GLOBAL commands
	fmt.Println("Clearing global commands...")
	commands, err := b.Client.Rest.GetGlobalCommands(b.Client.ApplicationID, false)
	if err != nil {
		return err
	}

	for _, cmd := range commands {
		if err := b.Client.Rest.DeleteGlobalCommand(b.Client.ApplicationID, cmd.ID()); err != nil {
			log.Printf("Error deleting global command %s: %v\n", cmd.Name, err)
		} else {
			fmt.Printf("✓ Deleted global command: %s\n", cmd.Name())
		}
	}

	return nil
}

func (b *Bot) OnReady(_ *events.Ready) {
	log.Info("DiscordCTFHelper ready")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := b.Client.SetPresence(ctx, gateway.WithListeningActivity("Setting up your CTF events..."), gateway.WithOnlineStatus(discord.OnlineStatusOnline)); err != nil {
		log.Error("Failed to set presence", "err", err)
	}

	log.Info("Starting presence status changer...")
	// Change presence every 10 minutes
	go changePresenceStatus(context.Background(), b.Client)
}

// Handle all the modal submission
func (b *Bot) modalListener(e *events.ModalSubmitInteractionCreate) {
	modalID := e.Data.CustomID
	log.Debug("Modal submitted", "modal_id", modalID, "user_id", e.User().ID)
	var content, username, password string
	var personal bool = false
	switch {
	case strings.HasPrefix(modalID, "creds_modal_"):
		// Gather all modal input values for logging or debugging
		for component := range e.Data.AllComponents() {
			if input, ok := component.(discord.TextInputComponent); ok {
				switch input.CustomID {
				case "username":
					username = input.Value
				case "password":
					password = input.Value
				}
				if input.CustomID == "personal" {
					personalInput := strings.ToLower(input.Value)
					if personalInput == "yes" {
						personal = true
					} else {
						personal = false
					}
				}
			}
		}

		ctfIDStr := strings.TrimPrefix(modalID, "creds_modal_")
		ctfID, err := strconv.Atoi(ctfIDStr)
		if err != nil {
			log.Error("Error parsing CTF ID from modal ID", "err", err, "modal_id", modalID)
			content = "Error processing modal submission."
			break
		}

		// Add credentials to the database
		err = b.Database.AddCreds(
			username,
			password,
			personal,
			int64(ctfID),
		)
		if err != nil {
			log.Error("Error adding credentials to database", "err", err, "ctf_id", ctfID)
			content = "Error saving credentials."
			break
		}
		content += "Credentials submitted ✅."
	default:
		content = "Unknown modal submitted."
	}

	if err := e.CreateMessage(discord.MessageCreate{
		Content: content,
	}); err != nil {
		log.Error("error creating modal", "err", err)
	}
}

func RemoveCTF(b *Bot, ctf database.CTFModel) error {
	channel, err := b.Client.Rest.GetChannel(ctf.TextChannelID)
	if err != nil {
		log.Error("Error fetching channel to remove CTF", "err", err, "channel_id", ctf.TextChannelID)
		return err
	}

	// Delete the channel
	if err := b.Client.Rest.DeleteChannel(ctf.TextChannelID); err != nil {
		log.Error("Error deleting channel for CTF", "err", err, "channel_id", ctf.TextChannelID)
		return err
	}
	log.Info("Deleted channel for CTF", "channel_id", channel.ID(), "ctf_time_id", ctf.CTFTimeID)

	// Delete the role if it exists
	if ctf.RoleID != 0 {
		if err := b.Client.Rest.DeleteRole(ctf.ServerID, ctf.RoleID); err != nil {
			log.Error("Error deleting role for CTF", "err", err, "role_id", ctf.RoleID)
			// Not returning error here, just logging
		} else {
			log.Info("Deleted role for CTF", "role_id", ctf.RoleID, "ctf_time_id", ctf.CTFTimeID)
		}
	}

	// Delete the event if it exists
	if ctf.EventID != 0 {
		if err := b.Client.Rest.DeleteGuildScheduledEvent(ctf.ServerID, ctf.EventID); err != nil {
			log.Error("Error deleting event for CTF", "err", err, "event_id", ctf.EventID)
			// Not returning error here, just logging
		} else {
			log.Info("Deleted event for CTF", "event_id", ctf.EventID, "ctf_time_id", ctf.CTFTimeID)
		}
	}

	server, err := b.Database.GetServerByID(ctf.ServerID)
	if err != nil {
		log.Error("Error fetching server for CTF removal", "err", err, "server_id", ctf.ServerID)
		return err
	}
	feedChannel, err := b.Client.Rest.GetChannel(server.FeedChannelID)
	if err != nil {
		log.Error("Error fetching feed channel for CTF removal", "err", err, "channel_id", server.FeedChannelID)
		return err
	}

	// Remove CTF announcement from feed channel
	if ctf.MsgID != 0 {
		if err := b.Client.Rest.DeleteMessage(feedChannel.ID(), ctf.MsgID); err != nil {
			log.Error("Error deleting feed message for CTF", "err", err, "msg_id", ctf.MsgID)
			// Not returning error here, just logging
		} else {
			log.Info("Deleted feed message for CTF", "msg_id", ctf.MsgID, "ctf_time_id", ctf.CTFTimeID)
		}
	}

	return nil
}

func (b *Bot) selectListener(e *events.ComponentInteractionCreate) {
	values := e.StringSelectMenuInteractionData().Values
	selectId := e.Data.CustomID()
	log.Debug("Select menu interaction", "values", values, "user_id", e.User().ID)
	if selectId != "remove_ctf_select" {
		return
	}

	for _, value := range values {
		valueInt, err := strconv.Atoi(value)
		if err != nil {
			log.Error("Error parsing CTFTime ID from select value", "err", err, "value", value)
			_ = e.CreateMessage(discord.MessageCreate{
				Content: "Errore durante l'elaborazione della selezione.",
				Flags:   discord.MessageFlagEphemeral,
			})
			return
		}

		ctf, err := b.Database.GetCTFByID(int64(valueInt))
		if err != nil {
			log.Error("Error fetching CTF by CTFTime ID", "err", err, "ctf_time_id", valueInt)
			_ = e.CreateMessage(discord.MessageCreate{
				Content: "Errore durante il recupero del CTF dal database.",
				Flags:   discord.MessageFlagEphemeral,
			})
			return
		}
		if ctf == nil {
			_ = e.CreateMessage(discord.MessageCreate{
				Content: fmt.Sprintf("Nessun CTF trovato con CTFTime ID %d.", valueInt),
				Flags:   discord.MessageFlagEphemeral,
			})
			return
		}

		if err := RemoveCTF(b, *ctf); err != nil {
			log.Error("Error removing CTF", "err", err, "ctf_time_id", valueInt)
			_ = e.CreateMessage(discord.MessageCreate{
				Content: "Errore durante la rimozione del CTF.",
				Flags:   discord.MessageFlagEphemeral,
			})
			return
		}

		// Delete CTF from database
		b.Database.DeleteCTF(int64(valueInt))
	}

	_ = e.CreateMessage(discord.MessageCreate{
		Content: "CTF removed successfully ✅.",
		Flags:   discord.MessageFlagEphemeral,
	})
}

func (b *Bot) pollListener(e *events.MessageCreate) {
	if e.Message.Type == discord.MessageTypePollResult {
		if e.Message.MessageReference == nil || e.Message.MessageReference.MessageID == nil {
			log.Error("Poll result message does not have a message reference")
			return
		}
		message, err := b.Client.Rest.GetMessage(e.ChannelID, *e.Message.MessageReference.MessageID)
		if err != nil {
			log.Error("Failed to fetch original message for poll result", "err", err, "message_id", e.Message.MessageReference.MessageID)
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
			log.Info("Risposta con più voti trovata", "answer", bestAnswer, "votes", maxVotes)
			ctftimeId := strings.TrimSpace(bestAnswer[strings.LastIndex(bestAnswer, "(")+1 : len(bestAnswer)-1])
			log.Info("CTFTime ID estratto", "ctf_time_id", ctftimeId)
			// ctfTimeIDInt, err := strconv.Atoi(ctftimeId)
			if err != nil {
				log.Error("Errore durante la conversione del CTFTime ID", "err", err, "ctf_time_id", ctftimeId)
				return
			}
			// serv, err := b.Database.GetServerByID(*e.GuildID)
			// trigger the creation of the CTF
		} else {
			log.Warn("Nessuna risposta trovata nel sondaggio")
		}
	}
}

func (b *Bot) messageListener(e *events.MessageCreate) {
	// Check if the message is a system message for a new member joining
	if e.Message.Type == discord.MessageTypeUserJoin {
		var cookieEmoji discord.Emoji
		emoji, err := b.Client.Rest.GetEmoji(*e.GuildID, 1365671553622343792)
		if err != nil {
			log.Error("Failed to fetch custom cookie~1 emoji", "err", err)
		} else {
			cookieEmoji = *emoji
		}
		found := cookieEmoji.ID != 0
		if found {
			if err := e.Client().Rest.AddReaction(e.ChannelID, e.Message.ID, cookieEmoji.String()); err != nil {
				log.Error("Failed to add custom cookie~1 emoji reaction", "err", err)
			}
		} else {
			if err := e.Client().Rest.AddReaction(e.ChannelID, e.Message.ID, "🍪"); err != nil {
				log.Error("Failed to add 🍪 emoji reaction", "err", err)
			}
		}
	}
}

func (b *Bot) reactionAddListener(e *events.MessageReactionAdd) {
	// Only handle guild reactions
	log.Debug("Reaction add event received", "message_id", e.MessageID, "user_id", e.UserID)
	if e.GuildID == nil {
		return
	}

	// Fetch the guild member who added the reaction
	member := e.Member
	if member == nil || member.User.Bot {
		return
	}

	log.Debug("Reaction add event", "message_id", e.MessageID, "user_id", member.User.ID)

	// Find CTF by message ID and guild ID
	ctf, err := b.Database.GetCTFByMessageID(e.MessageID, *e.GuildID)
	if err != nil {
		log.Error("Error fetching CTF by message ID", "err", err, "message_id", e.MessageID)
		return
	}
	if ctf == nil {
		log.Info("CTF not found for message", "message_id", e.MessageID)
		return
	}

	// Add the CTF role to the member
	if ctf.RoleID != 0 {
		if err := b.Client.Rest.AddMemberRole(*e.GuildID, member.User.ID, ctf.RoleID); err != nil {
			log.Error("Failed to add CTF role to member", "err", err, "role_id", ctf.RoleID, "user_id", member.User.ID)
		}
	}
}

func (b *Bot) reactionRemoveListener(e *events.MessageReactionRemove) {
	log.Debug("Reaction remove event received", "message_id", e.MessageID, "user_id", e.UserID)
	// Only handle guild reactions
	if e.GuildID == nil {
		return
	}

	member, err := b.Client.Rest.GetMember(*e.GuildID, e.UserID)
	if err != nil {
		log.Error("Failed to fetch member for reaction remove", "err", err, "user_id", e.UserID)
		return
	}
	if member.User.Bot {
		return
	}

	log.Debug("Reaction remove event", "message_id", e.MessageID, "user_id", member.User.ID)

	// Find CTF by message ID and guild ID
	ctf, err := b.Database.GetCTFByMessageID(e.MessageID, *e.GuildID)
	if err != nil {
		log.Error("Error fetching CTF by message ID", "err", err, "message_id", e.MessageID)
		return
	}
	if ctf == nil {
		log.Info("CTF not found for message", "message_id", e.MessageID)
		return
	}

	// Remove the CTF role from the member
	if ctf.RoleID != 0 {
		if err := b.Client.Rest.RemoveMemberRole(*e.GuildID, member.User.ID, ctf.RoleID); err != nil {
			log.Error("Failed to remove CTF role from member", "err", err, "role_id", ctf.RoleID, "user_id", member.User.ID)
		}
	} else {
		log.Info("Role not found for CTF", "ctf_name", ctf.Name)
	}
}

func (b *Bot) scheduledEventUpdateListener(e *events.GuildScheduledEventUpdate) {
	if b.Database == nil || &e.GuildScheduled.GuildID == nil {
		return
	}

	// Get CTF by event name and guild ID
	ctf, err := b.Database.GetCTFByName(e.GuildScheduled.Name, e.GuildScheduled.GuildID)
	if err != nil {
		log.Error("Error fetching CTF by name for scheduled event update", "err", err, "ctf_name", e.GuildScheduled.Name, "guild_id", e.GuildScheduled.GuildID)
		return
	}
	if ctf == nil {
		log.Info("CTF not found in database for scheduled event update", "ctf_name", e.GuildScheduled.Name)
		return
	}

	// If status changed to active, announce start
	if e.OldGuildScheduled.Status != e.GuildScheduled.Status && e.GuildScheduled.Status == discord.ScheduledEventStatusActive {
		channel, err := b.Client.Rest.GetChannel(ctf.TextChannelID)
		if err == nil && channel.Type() == discord.ChannelTypeGuildText {
			_, err := b.Client.Rest.CreateMessage(channel.ID(), discord.MessageCreate{
				Content: fmt.Sprintf("<@&%d> The CTF has started! Good luck to all participants! :tada:", ctf.RoleID),
			})
			if err != nil {
				log.Error("Failed to send CTF started message", "err", err, "channel_id", channel.ID())
			}
		}
	}

	// If status changed to completed, archive channel and update role
	if e.OldGuildScheduled.Status != e.GuildScheduled.Status && e.GuildScheduled.Status == discord.ScheduledEventStatusCompleted {
		channel, err := b.Client.Rest.GetChannel(ctf.TextChannelID)
		if err != nil {
			log.Error("Failed to fetch CTF text channel for archiving", "err", err, "channel_id", ctf.TextChannelID)
			return
		}
		server, err := b.Database.GetServerByID(ctf.ServerID)
		if err != nil {
			log.Error("Failed to fetch server for CTF archiving", "err", err, "server_id", ctf.ServerID)
			return
		}

		// Move channel to archive category if possible
		pos := 0
		if server != nil && server.ArchiveCategoryID != 0 && channel.Type() == discord.ChannelTypeGuildText {
			_, err := b.Client.Rest.UpdateChannel(channel.ID(), discord.GuildTextChannelUpdate{
				ParentID: &server.ArchiveCategoryID,
				Position: &pos,
			})
			if err != nil {
				log.Error("Failed to move channel to archive category", "err", err, "channel_id", channel.ID(), "archive_category_id", server.ArchiveCategoryID)
			}
		}

		// Update role color, hoist, mentionable
		if ctf.RoleID != 0 {
			_, err := b.Client.Rest.UpdateRole(ctf.ServerID, ctf.RoleID, discord.RoleUpdate{
				Color:       func(v int) *int { return &v }(0xD3D3D3),
				Hoist:       func(v bool) *bool { return &v }(false),
				Mentionable: func(v bool) *bool { return &v }(false),
			})
			if err != nil {
				log.Error("Failed to update CTF role after event completion", "err", err, "role_id", ctf.RoleID)
			}
		}

		// Send archive message
		if channel.Type() == discord.ChannelTypeGuildText {
			_, err := b.Client.Rest.CreateMessage(channel.ID(), discord.MessageCreate{
				Content: fmt.Sprintf("<@&%d> The CTF **%s** has ended! The channel has been moved to the archived category.", ctf.RoleID, ctf.Name),
			})
			if err != nil {
				log.Error("Failed to send CTF archived message", "err", err, "channel_id", channel.ID())
			}
		}
	}
}
