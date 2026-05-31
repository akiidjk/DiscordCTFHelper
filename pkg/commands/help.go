package commands

import (
	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var help = discord.SlashCommandCreate{
	Name:        "help",
	Description: "Get a list of available commands",
}

func HelpHandler() handler.CommandHandler {
	return func(e *handler.CommandEvent) error {
		if err := e.DeferCreateMessage(true); err != nil {
			log.Error("failed to defer create message", "error", err)
			return err
		}

		response := "Available commands:\n" +
			"/version - Get the bot version\n" +
			"/create - Create a new CTF event\n" +
			"/remove - Remove an existing CTF event\n" +
			"/flag - Submit a flag for a CTF event\n" +
			"/deleteflag - Delete a submitted flag\n" +
			"/report - Generate a report of CTF events and flags\n" +
			"/creds - Add credentials for a CTF event\n" +
			"/deletecreds - Delete credentials for a CTF event\n" +
			"/nextctfs - Get a list of upcoming CTF events\n" +
			"/cinit - Initialize the bot for a new server\n" +
			"/chall - Get information about a specific challenge\n" +
			"/vote - Vote for the next CTF event to be added\n" +
			"/ping - Check if the bot is alive\n" +
			"/help - Get a list of available commands\n"

		_, err := e.CreateFollowupMessage(discord.MessageCreate{
			Content: response,
			Flags:   discord.MessageFlagEphemeral,
		})
		return err
	}
}
