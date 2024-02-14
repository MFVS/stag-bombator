package main

import (
	"log/slog"
	"net/http"
)

func main() {
	root := http.NewServeMux()
	root.Handle("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Hello, World!"))
	}))
	server := http.Server{
		Handler: root,
	}
	slog.Info("Starting server", "addr", "0.0.0.0", "port", "8080")
	slog.Error(server.ListenAndServe().Error())
}
