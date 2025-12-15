package database

import (
	"database/sql"

	_ "embed"

	"github.com/charmbracelet/log"
	_ "github.com/mattn/go-sqlite3"
)

//go:embed schema.sql
var schema string

type Database struct {
	connection *sql.DB
}

func (db *Database) Close() {
	if db.connection != nil {
		err := db.connection.Close()
		if err != nil {
			log.Error("Failed to close database", "err", err)
		}
	}
}

func (db *Database) Connection() *sql.DB {
	return db.connection
}

func (db *Database) Init() error {
	var err error
	db.connection, err = sql.Open("sqlite3", "ctfs.db")
	if err != nil {
		log.Fatal(err)
	}

	_, err = db.connection.Exec(schema)
	if err != nil {
		log.Fatal(err)
	}

	return nil
}

// Singleton instance

var dbInstance *Database

func GetInstance() *Database {
	return dbInstance
}

func Setup() *Database {
	if dbInstance == nil {
		dbInstance = &Database{}
		err := dbInstance.Init()
		if err != nil {
			log.Fatal("Failed to setup database", "err", err)
		}
	}
	return dbInstance
}
