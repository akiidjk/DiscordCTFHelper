package commands

import "github.com/disgoorg/disgo/discord"

var Commands = []discord.ApplicationCommandCreate{
	version,
	create,
	remove,
	flag,
	delete_flag,
	report,
	creds,
	delete_creds,
	next_ctfs,
	cinit,
}
