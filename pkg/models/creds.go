package models

import (
	"time"

	"gorm.io/gorm"
)

// CredsModel represents credentials for a CTF
type CredsModel struct {
	gorm.Model
	ID        int64 `gorm:"primaryKey"`
	Username  string
	Password  string
	Personal  bool
	CTFID     int64 `gorm:"not null;uniqueIndex"`
	CreatedAt time.Time
	UpdatedAt time.Time
}

// AddCreds adds credentials to the database.
func (creds *CredsModel) AddCreds(db *gorm.DB) error {
	creds.UpdatedAt = time.Now()
	return db.Create(creds).Error
}

// GetCredsByCTFID retrieves credentials from the database for a specific CTF.
func (creds *CredsModel) GetCredsByCTFID(db *gorm.DB, ctfID int64) error {
	result := db.Where(CredsModel{CTFID: ctfID}).First(creds)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

// UpdateCreds updates credentials in the database. If they do not exist, it creates them.
func (creds *CredsModel) UpdateCreds(db *gorm.DB, ctfID int64) error {
	result := db.Model(&CredsModel{}).
		Where(CredsModel{CTFID: ctfID}).
		Updates(CredsModel{
			Username: creds.Username,
			Password: creds.Password,
			Personal: creds.Personal,
		})

	if result.Error != nil {
		return result.Error
	}

	if result.RowsAffected == 0 {
		creds.CTFID = ctfID
		return db.Create(creds).Error
	}

	return nil
}

// DeleteCreds deletes credentials from the database by CTFID.
func (creds *CredsModel) DeleteCreds(db *gorm.DB) error {
	return db.Delete(&CredsModel{}, CredsModel{CTFID: creds.CTFID}).Error
}
