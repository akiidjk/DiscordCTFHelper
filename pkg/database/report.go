package database

import (
	"database/sql"

	"github.com/charmbracelet/log"
)

// AddReport adds a report to the database.
func (db *Database) AddReport(report ReportModel) error {
	_, err := db.connection.Exec(
		`INSERT INTO reports (ctf_id, place, solves, score) VALUES (?, ?, ?, ?)`,
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
	err := db.connection.QueryRow(
		`SELECT id, ctf_id, place, solves, score FROM reports WHERE ctf_id = ?`,
		ctfID,
	).Scan(&report.ID, &report.CTFID, &report.Place, &report.Solves, &report.Score)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		log.Error("Failed to query report", "err", err)
		return nil, err
	}

	return &report, nil
}

// UpdateReport updates a report in the database. If it does not exist, it will not create it.
func (db *Database) UpdateReport(ctfID int64, report ReportModel) error {
	_, err := db.connection.Exec(
		`UPDATE reports SET place = ?, solves = ?, score = ? WHERE ctf_id = ?`,
		report.Place, report.Solves, report.Score, ctfID,
	)
	if err != nil {
		log.Error("Failed to update report", "err", err)
		return err
	}
	return nil
}
