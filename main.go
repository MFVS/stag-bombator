package main

import (
	"context"
	"log/slog"
	"net/http"
	"templates"
)

func main() {
	root := http.NewServeMux()
	root.Handle("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		// w.Write([]byte("Hello, World!"))
		templates.HTMLTemplate(templates.ExampleTemplate()).Render(context.Background(), w)
	}))
	server := http.Server{
		Handler: root,
		Addr:    ":8080",
	}
	slog.Info("Starting server", "addr", "0.0.0.0", "port", "8080")
	slog.Error(server.ListenAndServe().Error())
}
