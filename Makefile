.PHONY: build build-prod run lint fmt help

build:
	@go build -o bin/ctfhelper cmd/ctfhelper/main.go

build-prod:
	@echo "Building production binary for Linux (optimized for Docker)..."
	@env CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -tags "libsqlite3 linux" -trimpath -ldflags="-s -w" -o bin/ctfhelper cmd/ctfhelper/main.go

run: build
	@./bin/ctfhelper $(ARGS)

lint:
	@go work sync
	@go list -f {{.Dir}} -m | xargs golangci-lint run --fix

fmt:
	@go work sync
	@go list -f {{.Dir}} -m | xargs gofumpt -w -d

help:
	@echo "Available targets:"
	@echo "  build       - Build local binary"
	@echo "  build-prod  - Build optimized production binary for Linux (Docker)"
	@echo "  run         - Run the application"
	@echo "  lint        - Run golangci-lint"
	@echo "  fmt         - Format code (gofumpt if available, fallback to gofmt)"
	@echo "  help        - Show this help message"
