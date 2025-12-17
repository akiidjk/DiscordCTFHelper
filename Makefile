.PHONY: build build-prod run lint fmt help

build:
	@go build -o bin/ctfhelper cmd/ctfhelper/main.go

build-prod:
	@echo "Building production binary for Linux (optimized for Docker)..."
	@env CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -tags "libsqlite3 linux" -trimpath -ldflags="-s -w" -o bin/ctfhelper cmd/ctfhelper/main.go

run: build
	@./bin/ctfhelper $(ARGS)

lint:
	@if ! golangci-lint run ; then exit 1; fi

fmt:
	@if command -v gofumpt > /dev/null; then gofumpt -w -d .; else go list -f {{.Dir}} ./... | xargs gofmt -w -s -d; fi

help:
	@echo "Available targets:"
	@echo "  build       - Build local binary"
	@echo "  build-prod  - Build optimized production binary for Linux (Docker)"
	@echo "  run         - Run the application"
	@echo "  lint        - Run golangci-lint"
	@echo "  fmt         - Format code (gofumpt if available, fallback to gofmt)"
	@echo "  help        - Show this help message"
