import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    // Section 9.2: a progressive web app, so no app store is needed. The shell, fonts and code are
    // precached; demo map tiles are cached on first use. API data is kept in IndexedDB by the app.
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "auto",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "GeoGuard",
        short_name: "GeoGuard",
        start_url: "/alerts",
        scope: "/",
        display: "standalone",
        background_color: "#f1f2ef",
        theme_color: "#1d4f91",
        icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,woff2}"],
        maximumFileSizeToCacheInBytes: 6_000_000,
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/api/tiles/"),
            handler: "CacheFirst",
            options: { cacheName: "lp-tiles", expiration: { maxEntries: 5000 } },
          },
        ],
      },
    }),
  ],
  build: { outDir: "dist", sourcemap: false, chunkSizeWarningLimit: 1500 },
  server: { proxy: { "/api": { target: "http://api:8000", rewrite: (p) => p.replace(/^\/api/, "") } } },
});
