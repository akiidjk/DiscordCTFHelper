FROM golang:1.25.5-alpine AS builder

WORKDIR /app

COPY go.mod .
COPY go.sum .

RUN go mod download

COPY . .

ENV CGO_ENABLED=0

RUN go build -o ctfhelper ./cmd/ctfhelper

FROM gcr.io/distroless/static-debian12

COPY --from=builder /app/ctfbotd /ctfbotd

ENTRYPOINT ["/ctfhelper"]
