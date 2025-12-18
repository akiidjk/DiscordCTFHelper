package models

import (
	"time"

	"github.com/disgoorg/snowflake/v2"
	"gorm.io/gorm"
)

// CTFModel represents a CTF event
type CTFModel struct {
	gorm.Model
	ID            int64        `gorm:"primaryKey"`
	ServerID      snowflake.ID `gorm:"not null"`
	Name          string       `gorm:"not null"`
	Description   string
	TextChannelID snowflake.ID
	EventID       snowflake.ID
	RoleID        snowflake.ID
	MsgID         snowflake.ID
	CTFTimeID     int64
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

// AddCTF adds the CTF to the database.
func (ctf *CTFModel) AddCTF(db *gorm.DB) error {
	return db.Create(ctf).Error
}

// GetCTFByID retrieves a CTF by its ID.
func (ctf *CTFModel) GetCTFByID(db *gorm.DB, id int64) error {
	result := db.First(ctf, CTFModel{ID: id})
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

// GetCTFByName retrieves a CTF by name and server ID (LIKE match).
func (ctf *CTFModel) GetCTFByName(db *gorm.DB, name string, serverID snowflake.ID) error {
	result := db.Where("name LIKE ? AND server_id = ?", "%"+name+"%", serverID).First(ctf)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

// GetCTFByCTFTimeID retrieves a CTF by its CTFTimeID.
func (ctf *CTFModel) GetCTFByCTFTimeID(db *gorm.DB, ctftimeID int64) error {
	result := db.Where(CTFModel{CTFTimeID: ctftimeID}).First(ctf)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

// GetCTFByMessageID retrieves a CTF by message ID and server ID.
func (ctf *CTFModel) GetCTFByMessageID(db *gorm.DB, messageID, serverID snowflake.ID) error {
	result := db.Where(CTFModel{MsgID: messageID, ServerID: serverID}).First(ctf)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

// GetCTFByChannelID retrieves a CTF by text channel ID and server ID.
func (ctf *CTFModel) GetCTFByChannelID(db *gorm.DB, channelID, serverID snowflake.ID) error {
	result := db.Where(CTFModel{TextChannelID: channelID, ServerID: serverID}).First(ctf)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

// DeleteCTF deletes the CTF from the database by its ID.
func (ctf *CTFModel) DeleteCTF(db *gorm.DB) error {
	return db.Delete(&CTFModel{}, ctf.ID).Error
}

// IsCTFPresent checks if a CTF is present in the database by name and server ID.
func (ctf *CTFModel) IsCTFPresent(db *gorm.DB) (bool, error) {
	var count int64
	err := db.Model(&CTFModel{}).Where(CTFModel{Name: ctf.Name, ServerID: ctf.ServerID}).Count(&count).Error
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

// GetCTFsList retrieves a list of all CTFs for a specific server.
func (_ CTFModel) GetCTFsList(db *gorm.DB, serverID snowflake.ID) ([]CTFModel, error) {
	var ctfs []CTFModel
	err := db.Where(CTFModel{ServerID: serverID}).Find(&ctfs).Error
	if err != nil {
		return nil, err
	}
	return ctfs, nil
}
