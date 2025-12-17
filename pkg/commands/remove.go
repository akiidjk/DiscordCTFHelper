package commands

import (
	"strconv"

	ctfbot "ctfhelper/pkg/bot"
	"ctfhelper/pkg/database"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

var remove = discord.SlashCommandCreate{
	Name:        "remove",
	Description: "Remove a CTF event in the discord server.",
}

func ParseCtfsOptions(ctfs []database.CTFModel) []discord.StringSelectMenuOption {
	options := make([]discord.StringSelectMenuOption, 0, len(ctfs))
	for _, ctf := range ctfs {
		option := discord.NewStringSelectMenuOption(
			ctf.Name,
			strconv.Itoa(int(ctf.ID)),
		).WithDescription(ctf.Description)
		options = append(options, option)
	}
	return options
}

func RemoveHandler(b *ctfbot.Bot) handler.CommandHandler {
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

		ctfs, err := b.Database.GetCTFsList(*e.GuildID())

		msg := discord.MessageCreate{
			Content: "Seleziona un CTF:",
			Components: []discord.LayoutComponent{
				discord.NewActionRow(
					discord.NewStringSelectMenu(
						"remove_ctf_select",
						"Seleziona le CTF da rimuovere",
						ParseCtfsOptions(ctfs)...,
					).WithPlaceholder("Nessun CTF selezionato"),
				),
			},
		}

		_, err = e.CreateFollowupMessage(msg)
		return err
	}
}
