package database

import (
	"database/sql"

	"github.com/charmbracelet/log"
)

// AddCreds adds or updates credentials in the database.
// If credentials with the same ctf_id exist, update them; otherwise, insert new ones.
func (db *Database) AddCreds(username, password string, personal bool, ctfID int64) error {
	// Check if credentials already exist for this CTF
	var exists int
	err := db.connection.QueryRow("SELECT 1 FROM creds WHERE ctf_id = ?", ctfID).Scan(&exists)

	if err == sql.ErrNoRows {
		_, err = db.connection.Exec(
			`INSERT INTO creds (username, password, personal, ctf_id) VALUES (?, ?, ?, ?)`,
			username, password, personal, ctfID,
		)
		if err != nil {
			log.Error("failed to insert credentials", "err", err)
			return err
		}
	} else if err != nil {
		log.Error("failed to check existing credentials", "err", err)
		return err
	} else {
		_, err = db.connection.Exec(
			`UPDATE creds SET username = ?, password = ?, personal = ? WHERE ctf_id = ?`,
			username, password, personal, ctfID,
		)
		if err != nil {
			log.Error("failed to update credentials", "err", err)
			return err
		}
	}

	return nil
}

// DeleteCreds deletes credentials from the database.
func (db *Database) DeleteCreds(ctfID int64) bool {
	_, err := db.connection.Exec("DELETE FROM creds WHERE ctf_id = ?", ctfID)
	if err != nil {
		log.Error("failed to delete credentials", "err", err)
		return false
	}
	return true
}

// GetCreds retrieves credentials from the database for a specific CTF.
func (db *Database) GetCreds(ctfID int64) (CredsModel, error) {
	rows, err := db.connection.Query(
		`SELECT id, username, password, personal, ctf_id FROM creds WHERE ctf_id = ? LIMIT 1`,
		ctfID,
	)
	if err != nil {
		log.Error("failed to query credentials", "err", err)
		return CredsModel{}, err
	}
	defer rows.Close()

	var creds []CredsModel
	for rows.Next() {
		var cred CredsModel
		err := rows.Scan(&cred.ID, &cred.Username, &cred.Password, &cred.Personal, &cred.CTFID)
		if err != nil {
			log.Error("failed to scan credential row", "err", err)
			continue
		}
		creds = append(creds, cred)
	}

	if err = rows.Err(); err != nil {
		log.Error("Error iterating credentials rows", "err", err)
		return CredsModel{}, err
	}

	if len(creds) == 0 {
		return CredsModel{}, nil
	}

	log.Debug("Fetched credentials", "creds", creds)
	return creds[0], nil
}
