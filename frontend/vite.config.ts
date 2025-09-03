import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": {
        target: "ws://localhost:8000",
        ws: true
      },
      // NEW: This line will catch requests to /static/uploads/*
      "/static/uploads": "http://localhost:8000",
      // Ensure thumbnails are also proxied correctly
      "/static/thumbnails": "http://localhost:8000"
    }
  }
});