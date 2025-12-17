package database

import (
	"time"

	"database/sql"

	"github.com/charmbracelet/log"
)

// AddReport adds a report to the database.
func (db *Database) AddReport(report ReportModel) error {
	_, err := db.connection.Exec(
		`INSERT INTO reports (ctf_id, place, solves, score, last_update) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`,
		report.CTFID, report.Place, report.Solves, report.Score,
	)
	if err != nil {
		log.Error("Failed to insert report", "err", err)
		return err
	}
	return nil
}

// GetReport retrieves a report from the database for a specific CTF.
func (db *Database) GetReport(ctfID int64) (*ReportModel, error) {
	var report ReportModel
	var lastUpdateStr string
	err := db.connection.QueryRow(
		`SELECT id, ctf_id, place, solves, score, last_update FROM reports WHERE ctf_id = ?`,
		ctfID,
	).Scan(&report.ID, &report.CTFID, &report.Place, &report.Solves, &report.Score, &lastUpdateStr)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		log.Error("Failed to query report", "err", err)
		return nil, err
	}

	// Parse lastUpdateStr into time.Time
	lastUpdate, err := time.Parse("2006-01-02 15:04:05", lastUpdateStr)
	if err != nil {
		log.Error("Failed to parse last_update", "err", err, "value", lastUpdateStr)
		return nil, err
	}
	report.LastUpdate = lastUpdate

	return &report, nil
}

// UpdateReport updates a report in the database. If it does not exist, it creates it.
func (db *Database) UpdateReport(ctfID int64, report ReportModel) error {
	res, err := db.connection.Exec(
		`UPDATE reports SET place = ?, solves = ?, score = ?, last_update = CURRENT_TIMESTAMP WHERE ctf_id = ?`,
		report.Place, report.Solves, report.Score, ctfID,
	)
	if err != nil {
		log.Error("Failed to update report", "err", err)
		return err
	}

	rowsAffected, err := res.RowsAffected()
	if err != nil {
		log.Error("Failed to get rows affected after update", "err", err)
		return err
	}

	if rowsAffected == 0 {
		_, err := db.connection.Exec(
			`INSERT INTO reports (ctf_id, place, solves, score, last_update) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`,
			ctfID, report.Place, report.Solves, report.Score,
		)
		if err != nil {
			log.Error("Failed to insert report after update not found", "err", err)
			return err
		}
	}

	return nil
}
