package database

import (
	"database/sql"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/snowflake/v2"
)

// AddCTF adds a CTF to the database.
func (db *Database) AddCTF(ctf CTFModel) error {
	_, err := db.connection.Exec(
		`INSERT INTO ctfs (server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		ctf.ServerID, ctf.Name, ctf.Description, ctf.TextChannelID, ctf.EventID, ctf.RoleID, ctf.MsgID, ctf.CTFTimeID,
	)
	if err != nil {
		log.Error("failed to insert CTF", "err", err)
		return err
	}
	return nil
}

// GetCTFByName retrieves a CTF from the database by name and server ID.
func (db *Database) GetCTFByName(name string, serverID snowflake.ID) (*CTFModel, error) {
	var ctf CTFModel
	err := db.connection.QueryRow(
		`SELECT id, server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id
		FROM ctfs WHERE name LIKE ? AND server_id = ?`,
		"%"+name+"%", serverID,
	).Scan(&ctf.ID, &ctf.ServerID, &ctf.Name, &ctf.Description, &ctf.TextChannelID, &ctf.EventID, &ctf.RoleID, &ctf.MsgID, &ctf.CTFTimeID)

	if err == sql.ErrNoRows {
		log.Debug("CTF not found", "name", name, "server_id", serverID)
		return nil, nil
	}
	if err != nil {
		log.Error("failed to query CTF by name", "err", err)
		return nil, err
	}

	log.Debug("CTF found", "id", ctf.ID, "name", ctf.Name)
	return &ctf, nil
}

// GetCTFByID retrieves a CTF from the database by its ID.
func (db *Database) GetCTFByID(id int64) (*CTFModel, error) {
	var ctf CTFModel
	err := db.connection.QueryRow(
		`SELECT id, server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id
		FROM ctfs WHERE id = ?`,
		id,
	).Scan(&ctf.ID, &ctf.ServerID, &ctf.Name, &ctf.Description, &ctf.TextChannelID, &ctf.EventID, &ctf.RoleID, &ctf.MsgID, &ctf.CTFTimeID)

	if err == sql.ErrNoRows {
		log.Debug("CTF not found", "ctf_id", id)
		return nil, nil
	}
	if err != nil {
		log.Error("failed to query CTF by ID", "err", err)
		return nil, err
	}

	log.Debug("CTF found", "id", ctf.ID, "name", ctf.Name)
	return &ctf, nil
}

// GetCTFByID retrieves a CTF from the database by its ID.
func (db *Database) GetCTFByCTFTimeID(ctftimeID int64) (*CTFModel, error) {
	var ctf CTFModel
	err := db.connection.QueryRow(
		`SELECT id, server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id
		FROM ctfs WHERE ctftime_id = ?`,
		ctftimeID,
	).Scan(&ctf.ID, &ctf.ServerID, &ctf.Name, &ctf.Description, &ctf.TextChannelID, &ctf.EventID, &ctf.RoleID, &ctf.MsgID, &ctf.CTFTimeID)

	if err == sql.ErrNoRows {
		log.Debug("CTF not found", "ctftime_id", ctftimeID)
		return nil, nil
	}
	if err != nil {
		log.Error("failed to query CTF by ID", "err", err)
		return nil, err
	}

	log.Debug("CTF found", "id", ctf.ID, "name", ctf.Name)
	return &ctf, nil
}

// DeleteCTF deletes a CTF from the database by its ID.
func (db *Database) DeleteCTF(ctfID int64) bool {
	_, err := db.connection.Exec("DELETE FROM ctfs WHERE id = ?", ctfID)
	if err != nil {
		log.Error("failed to delete CTF", "err", err)
		return false
	}
	return true
}

// GetCTFByMessageID retrieves a CTF from the database by message ID and server ID.
func (db *Database) GetCTFByMessageID(messageID, serverID snowflake.ID) (*CTFModel, error) {
	var ctf CTFModel
	err := db.connection.QueryRow(
		`SELECT id, server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id
		FROM ctfs WHERE msg_id = ? AND server_id = ?`,
		messageID, serverID,
	).Scan(&ctf.ID, &ctf.ServerID, &ctf.Name, &ctf.Description, &ctf.TextChannelID, &ctf.EventID, &ctf.RoleID, &ctf.MsgID, &ctf.CTFTimeID)

	if err == sql.ErrNoRows {
		log.Debug("CTF not found", "msg_id", messageID, "server_id", serverID)
		return nil, nil
	}
	if err != nil {
		log.Error("failed to query CTF by message ID", "err", err)
		return nil, err
	}

	log.Debug("CTF found", "id", ctf.ID, "name", ctf.Name)
	return &ctf, nil
}

// GetCTFByChannelID retrieves a CTF from the database by text channel ID and server ID.
func (db *Database) GetCTFByChannelID(channelID, serverID snowflake.ID) (*CTFModel, error) {
	var ctf CTFModel
	err := db.connection.QueryRow(
		`SELECT id, server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id
		FROM ctfs WHERE text_channel_id = ? AND server_id = ?`,
		channelID, serverID,
	).Scan(&ctf.ID, &ctf.ServerID, &ctf.Name, &ctf.Description, &ctf.TextChannelID, &ctf.EventID, &ctf.RoleID, &ctf.MsgID, &ctf.CTFTimeID)

	if err == sql.ErrNoRows {
		log.Debug("CTF not found", "channel_id", channelID, "server_id", serverID)
		return nil, nil
	}
	if err != nil {
		log.Error("failed to query CTF by channel ID", "err", err)
		return nil, err
	}

	log.Debug("CTF found", "id", ctf.ID, "name", ctf.Name)
	return &ctf, nil
}

// IsCTFPresent checks if a CTF is present in the database by name and server ID.
func (db *Database) IsCTFPresent(name string, serverID snowflake.ID) (bool, error) {
	var exists int
	err := db.connection.QueryRow(
		`SELECT 1 FROM ctfs WHERE name = ? AND server_id = ?`,
		name, serverID,
	).Scan(&exists)

	if err == sql.ErrNoRows {
		log.Debug("CTF not present", "name", name, "server_id", serverID)
		return false, nil
	}
	if err != nil {
		log.Error("failed to check CTF presence", "err", err)
		return false, err
	}

	log.Warn("CTF is present", "name", name, "server_id", serverID)
	return true, nil
}

// GetCTFsList retrieves a list of all CTFs for a specific server.
func (db *Database) GetCTFsList(serverID snowflake.ID) ([]CTFModel, error) {
	rows, err := db.connection.Query(
		`SELECT id, server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id
		FROM ctfs WHERE server_id = ?`,
		serverID,
	)
	if err != nil {
		log.Error("failed to query CTFs list", "err", err)
		return nil, err
	}
	defer rows.Close()

	var ctfs []CTFModel
	for rows.Next() {
		var ctf CTFModel
		err := rows.Scan(&ctf.ID, &ctf.ServerID, &ctf.Name, &ctf.Description, &ctf.TextChannelID, &ctf.EventID, &ctf.RoleID, &ctf.MsgID, &ctf.CTFTimeID)
		if err != nil {
			log.Error("failed to scan CTF row", "err", err)
			continue
		}
		ctfs = append(ctfs, ctf)
	}

	if err = rows.Err(); err != nil {
		log.Error("Error iterating CTF rows", "err", err)
		return nil, err
	}

	return ctfs, nil
}
