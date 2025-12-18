package database

import (
	_ "embed"
	"models"
	"sync"

	"gorm.io/driver/sqlite"

	"github.com/charmbracelet/log"
	"gorm.io/gorm"
)

type Database struct {
	connection *gorm.DB
}

func (db *Database) Connection() *gorm.DB {
	return db.connection
}

func (db *Database) Init() error {
	var err error
	db.connection, err = gorm.Open(sqlite.Open("ctfs.db"), &gorm.Config{})
	if err != nil {
		log.Fatal("failed to connect database")
	}

	err = db.connection.AutoMigrate(&models.Server{}, &models.CTF{}, &models.Report{}, &models.Creds{})
	if err != nil {
		log.Fatal(err)
	}

	return nil
}

// Singleton instance
var (
	dbInstance *Database
	once       sync.Once
)

func GetInstance() *Database {
	return dbInstance
}

func Setup() *Database {
	once.Do(func() {
		dbInstance = &Database{}
		if err := dbInstance.Init(); err != nil {
			log.Fatal("failed to setup database", "err", err)
		}
	})
	return dbInstance
}
