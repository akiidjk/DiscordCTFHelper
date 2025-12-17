package database

import (
	"database/sql"

	"github.com/charmbracelet/log"
	"github.com/disgoorg/snowflake/v2"
)

// AddServer adds a server to the database.
func (db *Database) AddServer(server ServerModel) error {
	_, err := db.connection.Exec(
		`INSERT INTO servers (id, active_category_id, archive_category_id, role_manager_id, feed_channel_id, team_id, role_team_id)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		server.ID, server.ActiveCategoryID, server.ArchiveCategoryID, server.RoleManagerID, server.FeedChannelID, server.TeamID, server.RoleTeamID,
	)
	if err != nil {
		log.Error("failed to insert server", "err", err)
		return err
	}
	return nil
}

// GetServerByID retrieves a server from the database by its ID.
func (db *Database) GetServerByID(serverID snowflake.ID) (*ServerModel, error) {
	var server ServerModel
	err := db.connection.QueryRow(
		`SELECT id, active_category_id, archive_category_id, role_manager_id, feed_channel_id, team_id, role_team_id
		FROM servers WHERE id = ?`,
		serverID,
	).Scan(&server.ID, &server.ActiveCategoryID, &server.ArchiveCategoryID, &server.RoleManagerID, &server.FeedChannelID, &server.TeamID, &server.RoleTeamID)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		log.Error("failed to query server", "err", err)
		return nil, err
	}

	return &server, nil
}

// EditCategory updates the category IDs for a server.
func (db *Database) EditCategory(server ServerModel) error {
	_, err := db.connection.Exec(
		`UPDATE servers SET active_category_id = ?, archive_category_id = ? WHERE id = ?`,
		server.ActiveCategoryID, server.ArchiveCategoryID, server.ID,
	)
	if err != nil {
		log.Error("failed to update server categories", "err", err)
		return err
	}
	return nil
}

// DeleteServer deletes a server from the database by its ID.
func (db *Database) DeleteServer(serverID snowflake.ID) error {
	_, err := db.connection.Exec("DELETE FROM servers WHERE id = ?", serverID)
	if err != nil {
		log.Error("failed to delete server", "err", err)
		return err
	}
	return nil
}
