package discord

import (
	"fmt"
	"time"

	ctfbot "ctfhelper/pkg/bot"
	"ctfhelper/pkg/ctftime"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
	"github.com/disgoorg/disgo/rest"
	"github.com/disgoorg/snowflake/v2"
	"golang.org/x/exp/rand"
)

func CheckPermission(b *ctfbot.Bot, e *handler.CommandEvent) error {
	sendEphemeral := func(content string) error {
		_, err := e.CreateFollowupMessage(discord.MessageCreate{
			Content: content,
			Flags:   discord.MessageFlagEphemeral,
		})
		return err
	}

	guildID := e.GuildID()
	if guildID == nil {
		return sendEphemeral("Guild not found. ❌")
	}

	guild, err := b.Client.Rest().GetGuild(*guildID, false)
	if err != nil {
		return err
	}

	server, err := b.Database.GetServerByID(*guildID)
	if err != nil {
		return err
	}
	if server == nil {
		return sendEphemeral("Server configuration not found. ❌")
	}

	var roleManager *discord.Role
	for i := range guild.Roles {
		if guild.Roles[i].ID == server.RoleManagerID {
			roleManager = &guild.Roles[i]
			break
		}
	}
	member := e.Member()

	hasRole := false
	if member != nil && roleManager != nil {
		for _, roleID := range member.RoleIDs {
			if roleID == roleManager.ID {
				hasRole = true
				break
			}
		}
	}

	if member == nil || roleManager == nil || !hasRole {
		return sendEphemeral("You don't have the required role to run this command. ❌")
	}

	return nil
}

func SendError(e *handler.CommandEvent, function string) error {
	_, err := e.CreateFollowupMessage(discord.MessageCreate{
		Content: fmt.Sprintf("Failed to get the %s. ❌", function),
		Flags:   discord.MessageFlagEphemeral,
	})
	return err
}

func CreateEvents(b *ctfbot.Bot, e *handler.CommandEvent, info ctftime.Event, eventDescription string, startTime time.Time, endTime time.Time) (discord.GuildScheduledEvent, error) {
	guildID := e.GuildID()
	if guildID == nil {
		return discord.GuildScheduledEvent{}, SendError(e, "event")
	}

	imageLogo, imageType, err := ctftime.GetLogo(info.Logo)
	if err != nil {
		return discord.GuildScheduledEvent{}, err
	}
	log.Debug("Creating event with logo", "imageType", imageType)

	image := &discord.Icon{
		Data: imageLogo,
		Type: discord.IconType(imageType),
	}

	scheduledEvent, err := b.Client.Rest().CreateGuildScheduledEvent(*guildID, discord.GuildScheduledEventCreate{
		Name:               info.Title,
		Description:        eventDescription,
		ScheduledStartTime: startTime,
		ScheduledEndTime:   &endTime,
		EntityType:         discord.ScheduledEventEntityTypeExternal,
		PrivacyLevel:       discord.ScheduledEventPrivacyLevelGuildOnly,
		Image:              image,
		EntityMetaData: &discord.EntityMetaData{
			Location: info.URL,
		},
	})
	if err != nil {
		if restErr, ok := err.(*rest.Error); ok && restErr.Message == "Unsupported image type given" {
			return CreateEvents(b, e, info, eventDescription, startTime, endTime)
		}
		_, _ = e.CreateFollowupMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Failed to create the event. ❌\nError: %s", err.Error()),
			Flags:   discord.MessageFlagEphemeral,
		})
		return discord.GuildScheduledEvent{}, err
	}

	return *scheduledEvent, nil
}

func CreateChannel(b *ctfbot.Bot, e *handler.CommandEvent, channelName string, categoryID snowflake.ID, roleID snowflake.ID, managerID snowflake.ID) (*discord.GuildChannel, error) {
	log.Debug("CreateChannel called with",
		"channelName", channelName,
		"categoryID", categoryID,
		"roleID", roleID,
		"managerID", managerID,
	)

	guildID := e.GuildID()
	if guildID == nil {
		log.Debug("GuildID is nil in CreateChannel")
		return nil, SendError(e, "channel")
	}

	log.Debug("Fetching category channel", "categoryID", categoryID)
	category, err := b.Client.Rest().GetChannel(categoryID)
	if err != nil {
		log.Debug("Failed to fetch category channel", "err", err)
	}
	if err != nil || category.Type() != discord.ChannelTypeGuildCategory {
		log.Debug("Category channel is invalid or not a category", "type", category.Type())
		return nil, SendError(e, "category")
	}

	var everyoneID *snowflake.ID
	roles, err := b.Client.Rest().GetRoles(*e.GuildID())
	if err != nil {
		log.Debug("Failed to fetch roles", "err", err)
		return nil, SendError(e, "roles")
	}
	for _, role := range roles {
		if role.Name == "@everyone" {
			log.Debug("Found @everyone role", "roleID", role.ID)
			everyoneID = &role.ID
			break
		}
	}

	if everyoneID == nil {
		log.Debug("Could not find @everyone role in guild", "guildID", *guildID)
		return nil, SendError(e, "@everyone role")
	}

	log.Debug("Creating guild text channel",
		"channelName", channelName,
		"categoryID", categoryID,
	)
	channel, err := b.Client.Rest().CreateGuildChannel(*guildID, discord.GuildTextChannelCreate{
		Name:     channelName,
		ParentID: categoryID,
		PermissionOverwrites: []discord.PermissionOverwrite{
			discord.RolePermissionOverwrite{
				RoleID: *everyoneID,
				Deny:   discord.PermissionViewChannel,
			},
			discord.RolePermissionOverwrite{
				RoleID: roleID,
				Allow:  discord.PermissionViewChannel | discord.PermissionSendMessages,
			},
			discord.RolePermissionOverwrite{
				RoleID: managerID,
				Deny:   discord.PermissionViewChannel,
			},
		},
	})
	if err != nil {
		log.Debug("Failed to create guild channel", "err", err)
		_, _ = e.CreateFollowupMessage(discord.MessageCreate{
			Content: fmt.Sprintf("Failed to create the channel or assign the permission. ❌\nError: %s", err.Error()),
			Flags:   discord.MessageFlagEphemeral,
		})
		return nil, err
	}

	log.Debug("Successfully created channel",
		"channelName", channel.Name(),
		"channelID", channel.ID(),
	)
	return &channel, nil
}

func CreateEmbed(b *ctfbot.Bot, data ctftime.Event, startTime time.Time, endTime time.Time, channel discord.Channel) (*discord.Message, error) {
	description := fmt.Sprintf(`
**Description:**

%s

- **Start Time:** <t:%d:f>
- **End Time:** <t:%d:f>
- **URL:** %s
- **Format:** %s
- **Location:** %s
- **Weight:** %s
- **Prizes:**
%s

`, data.Description, int(startTime.Unix()), int(endTime.Unix()), data.URL, data.Format, data.Location, data.Weight, data.Prizes)

	t := time.Now()
	embed := discord.Embed{
		Title:       data.Title,
		Description: description,
		URL:         data.URL,
		Timestamp:   &t,
		Color:       0xBEBEFE,
		Thumbnail: &discord.EmbedResource{
			URL: data.Logo,
		},
		Footer: &discord.EmbedFooter{
			Text: "Add a reaction to get the ctf role (only if you want to participate). 🙃",
		},
	}

	message, err := b.Client.Rest().CreateMessage(channel.ID(), discord.MessageCreate{
		Embeds: []discord.Embed{embed},
	})
	if err != nil {
		return nil, err
	}

	// Add reaction
	err = b.Client.Rest().AddReaction(channel.ID(), message.ID, "✅")
	if err != nil {
		return nil, err
	}

	return message, nil
}

func CreateRole(b *ctfbot.Bot, e *handler.CommandEvent, name string) (*discord.Role, error) {
	guildID := e.GuildID()
	if guildID == nil {
		return nil, nil
	}

	color := rand.Intn(0xFFFFFF)
	for color == 0xBEBEFE {
		color = rand.Intn(0xFFFFFF)
	}

	role, err := b.Client.Rest().CreateRole(*guildID, discord.RoleCreate{
		Name:        name,
		Color:       color,
		Mentionable: true,
		Hoist:       true,
	})
	return role, err
}
