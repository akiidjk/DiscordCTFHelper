package database

import "github.com/disgoorg/snowflake/v2"

// ServerModel represents a Discord server configuration
type ServerModel struct {
	ID                snowflake.ID
	ActiveCategoryID  snowflake.ID
	ArchiveCategoryID snowflake.ID
	RoleManagerID     snowflake.ID
	FeedChannelID     snowflake.ID
	TeamID            int64
	RoleTeamID        snowflake.ID
}

// CTFModel represents a CTF event
type CTFModel struct {
	ID            int64
	ServerID      snowflake.ID
	Name          string
	Description   string
	TextChannelID snowflake.ID
	EventID       snowflake.ID
	RoleID        snowflake.ID
	MsgID         snowflake.ID
	CTFTimeID     int64
}

// ReportModel represents a CTF report with results
type ReportModel struct {
	ID     int64
	CTFID  int64
	Place  int
	Solves int
	Score  int
}

// CredsModel represents credentials for a CTF
type CredsModel struct {
	ID       int64
	Username string
	Password string
	Personal bool
	CTFID    int64
}
