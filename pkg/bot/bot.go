package ctfbot

import (
	"context"
	"fmt"
	"time"

	"ctfhelper/pkg"
	"ctfhelper/pkg/database"

	"github.com/charmbracelet/log"

	"github.com/disgoorg/disgo"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/cache"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/events"
	"github.com/disgoorg/disgo/gateway"
	"github.com/disgoorg/paginator"
	"github.com/disgoorg/snowflake/v2"
)

var STATUSES = []string{
	"Setting up your CTF events...",
	"Syncing with CTFTime's latest info...",
	"Retrieving event details from CTFTime...",
	"Preparing for your next CTF event...",
}

func New(cfg pkg.Config, version string, commit string) *Bot {
	return &Bot{
		Cfg:       cfg,
		Paginator: paginator.New(),
		Version:   version,
		Commit:    commit,
	}
}

type Bot struct {
	Cfg       pkg.Config
	Client    bot.Client
	Paginator *paginator.Manager
	Version   string
	Commit    string
	Database  *database.Database
}

func (b *Bot) SetupBot(listeners ...bot.EventListener) error {
	client, err := disgo.New(b.Cfg.Bot.Token,
		bot.WithGatewayConfigOpts(gateway.WithIntents(gateway.IntentGuilds, gateway.IntentGuildMessages, gateway.IntentMessageContent)),
		bot.WithCacheConfigOpts(cache.WithCaches(cache.FlagGuilds)),
		bot.WithEventListeners(b.Paginator),
		bot.WithEventListeners(listeners...),
	)
	if err != nil {
		return err
	}

	b.Client = client
	return nil
}

func changePresenceStatus(ctx context.Context, client bot.Client) error {
	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			status := STATUSES[time.Now().UnixNano()%int64(len(STATUSES))]
			client.SetPresence(
				ctx,
				gateway.WithOnlineStatus(discord.OnlineStatusOnline),
				gateway.WithListeningActivity(status),
			)
			cancel()
		}
	}
}

// Delete all commands from Discord
func (b *Bot) resetAllCommands(guildID *snowflake.ID) error {
	if guildID != nil {
		// Delete GUILD-SPECIFIC commands
		fmt.Printf("Clearing guild commands for guild %d...\n", *guildID)
		commands, err := b.Client.Rest().GetGuildCommands(b.Client.ApplicationID(), *guildID, false)
		if err != nil {
			return err
		}

		for _, cmd := range commands {
			if err := b.Client.Rest().DeleteGuildCommand(b.Client.ApplicationID(), *guildID, cmd.ID()); err != nil {
				log.Printf("Error deleting guild command %s: %v\n", cmd.Name, err)
			} else {
				fmt.Printf("✓ Deleted guild command: %s\n", cmd.Name())
			}
		}
	} else {
		// Delete GLOBAL commands
		fmt.Println("Clearing global commands...")
		commands, err := b.Client.Rest().GetGlobalCommands(b.Client.ApplicationID(), false)
		if err != nil {
			return err
		}

		for _, cmd := range commands {
			if err := b.Client.Rest().DeleteGlobalCommand(b.Client.ApplicationID(), cmd.ID()); err != nil {
				log.Printf("Error deleting global command %s: %v\n", cmd.Name, err)
			} else {
				fmt.Printf("✓ Deleted global command: %s\n", cmd.Name())
			}
		}
	}

	return nil
}

func (b *Bot) OnReady(_ *events.Ready) {
	log.Info("DiscordCTFHelper ready")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// var guildID *snowflake.ID = nil
	// if err := b.resetAllCommands(guildID); err != nil {
	// 	log.Error("Failed to reset commands", "err", err)
	// }

	if err := b.Client.SetPresence(ctx, gateway.WithListeningActivity("Setting up your CTF events..."), gateway.WithOnlineStatus(discord.OnlineStatusOnline)); err != nil {
		log.Error("Failed to set presence", "err", err)
	}

	// Change presence every 10 minutes
	go changePresenceStatus(context.Background(), b.Client)
}
