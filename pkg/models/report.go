package models

import (
	"time"

	"gorm.io/gorm"
)

// ReportModel represents a CTF report with results
type ReportModel struct {
	gorm.Model
	ID        int64 `gorm:"primaryKey"`
	CTFID     int64 `gorm:"not null;index"`
	Place     int
	Solves    int
	Score     int
	CreatedAt time.Time
	UpdatedAt time.Time
}

// AddReport adds a report to the database.
func (report *ReportModel) AddReport(db *gorm.DB) error {
	report.UpdatedAt = time.Now()
	return db.Create(report).Error
}

// GetReportByCTFID retrieves a report from the database for a specific CTF.
func (report *ReportModel) GetReportByCTFID(db *gorm.DB, ctfID int64) error {
	result := db.Where(ReportModel{CTFID: ctfID}).First(report)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil
		}
		return result.Error
	}
	return nil
}

// UpdateReport updates a report in the database. If it does not exist, it creates it.
func (report *ReportModel) UpdateReport(db *gorm.DB) error {
	result := db.Model(&ReportModel{}).
		Where(ReportModel{CTFID: report.CTFID}).
		Updates(ReportModel{
			Place:  report.Place,
			Solves: report.Solves,
			Score:  report.Score,
		})

	if result.Error != nil {
		return result.Error
	}

	if result.RowsAffected == 0 {
		return db.Create(report).Error
	}

	return nil
}

// DeleteReport deletes a report from the database by CTFID.
func (_ *ReportModel) DeleteReport(db *gorm.DB, ctfID int64) error {
	return db.Delete(&ReportModel{}, ReportModel{CTFID: ctfID}).Error
}
