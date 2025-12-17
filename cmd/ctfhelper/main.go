package main

import (
	"context"
	"flag"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/charmbracelet/log"

	"ctfhelper/pkg"
	ctfbot "ctfhelper/pkg/bot"
	"ctfhelper/pkg/commands"
	"ctfhelper/pkg/database"
	"ctfhelper/pkg/handlers"

	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/handler"
	dotenv "github.com/dotenv-org/godotenvvault"
)

var (
	Version = "dev"
	Commit  = "2.0.0"
)

func init() {
	err := dotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}
}

func main() {
	shouldSyncCommands := flag.Bool("sync-commands", false, "Whether to sync commands to discord")
	shouldCleanCommands := flag.Bool("clean-commands", false, "Whether to clean commands from discord")
	flag.Parse()

	cfg, err := pkg.LoadConfig()
	if err != nil {
		log.Error("Failed to read config", "err", err)
		os.Exit(-1)
	}

	setupLogger(cfg.Log)
	log.Info("Starting bot-template...", "version", Version, "commit", Commit)
	log.Info("Syncing commands", "sync", *shouldSyncCommands)

	b := ctfbot.New(*cfg, Version, Commit)
	b.Database = database.Setup()
	defer b.Database.Close()

	h := handler.New()

	// Command registrations
	h.Command("/version", commands.VersionHandler(b))
	h.Command("/create", commands.CreateHandler(b))
	h.Command("/remove", commands.RemoveHandler(b))
	h.Command("/flag", commands.FlagHandler(b))
	h.Command("/delete-flag", commands.DeleteFlagHandler(b))
	h.Command("/report", commands.ReportHandler(b))
	h.Command("/creds", commands.CredsHandler(b))
	h.Command("/delete-creds", commands.DeleteCredsHandler(b))
	h.Command("/next-ctfs", commands.NextCTFsHandler(b))
	h.Command("/init", commands.InitHandler(b))
	h.Command("/chall", commands.ChallHandler(b))
	h.Command("/vote", commands.VoteHandler(b))

	if err = b.SetupBot(shouldCleanCommands, h, bot.NewListenerFunc(b.OnReady), handlers.MessageHandler(b)); err != nil {
		log.Error("Failed to setup bot", "err", err)
		os.Exit(-1)
	}

	defer func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		b.Client.Close(ctx)
	}()

	if *shouldSyncCommands {
		log.Info("Syncing commands", "guild_ids", cfg.Bot.DevGuilds)
		if err = handler.SyncCommands(&b.Client, commands.Commands, cfg.Bot.DevGuilds); err != nil {
			log.Error("Failed to sync commands", "err", err)
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err = b.Client.OpenGateway(ctx); err != nil {
		log.Error("Failed to open gateway", "err", err)
		os.Exit(-1)
	}

	log.Info("Bot is running. Press CTRL-C to exit.")
	s := make(chan os.Signal, 1)
	signal.Notify(s, syscall.SIGINT, syscall.SIGTERM)
	<-s
	log.Info("Shutting down bot...")
}

func setupLogger(cfg pkg.LogConfig) {
	opts := log.Options{
		Level:           cfg.Level,
		ReportCaller:    cfg.AddSource,
		ReportTimestamp: true,
		TimeFormat:      time.Kitchen,
	}

	logger := log.NewWithOptions(os.Stdout, opts)

	switch cfg.Format {
	case "json":
		logger.SetFormatter(log.JSONFormatter)
	case "text":
		logger.SetFormatter(log.TextFormatter)
	default:
		log.Error("Unknown log format", "format", cfg.Format)
	}

	log.SetDefault(logger)
}
