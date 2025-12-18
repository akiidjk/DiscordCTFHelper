package models

import (
	"time"

	"github.com/disgoorg/snowflake/v2"
	"gorm.io/gorm"
)

// ServerModel represents a Discord server configuration
type ServerModel struct {
	gorm.Model
	ID                snowflake.ID `gorm:"primaryKey"`
	ActiveCategoryID  snowflake.ID
	ArchiveCategoryID snowflake.ID
	RoleManagerID     snowflake.ID
	FeedChannelID     snowflake.ID
	TeamID            int64
	RoleTeamID        snowflake.ID
	CreatedAt         time.Time
	UpdatedAt         time.Time
}

func (server *ServerModel) AddServer(db *gorm.DB) error {
	return db.Create(server).Error
}

func (server *ServerModel) GetServerByID(db *gorm.DB, serverID snowflake.ID) error {
	result := db.First(&server, ServerModel{ID: serverID})
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

func (server *ServerModel) EditCategory(db *gorm.DB, activeCategoryID, archiveCategoryID snowflake.ID) error {
	return db.Model(&ServerModel{}).
		Where(ServerModel{ID: server.ID}).
		Updates(ServerModel{
			ActiveCategoryID:  activeCategoryID,
			ArchiveCategoryID: archiveCategoryID,
		}).Error
}

func (server *ServerModel) DeleteServer(db *gorm.DB) error {
	return db.Delete(&ServerModel{}, ServerModel{ID: server.ID}).Error
}
