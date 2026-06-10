import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  base: './',
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'Vigie – Nive / Aviron Bayonnais',
        short_name: 'Vigie',
        description: 'Marée, débit, météo et renverse de courant au ponton de l’Aviron Bayonnais (Nive).',
        lang: 'fr',
        theme_color: '#0a6a8c',
        background_color: '#0b2f36',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '.',
        scope: '.',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2}'],
        globIgnores: ['**/Nive3D-*.js'],   // gros chunk Three.js : chargé/caché à la demande, pas au precache
        navigateFallback: 'index.html',
        runtimeCaching: [
          {
            // Chunk 3D (Three.js) : récupéré quand on ouvre la vue 3D, puis caché
            urlPattern: ({ url }) => /\/Nive3D-.*\.js$/.test(url.pathname),
            handler: 'CacheFirst',
            options: { cacheName: 'vigie-3d', expiration: { maxEntries: 3 } },
          },
          {
            // Données marée/débit : réseau d'abord (frais si en ligne), cache si hors-ligne
            urlPattern: ({ url }) => url.pathname.includes('/data/') && url.pathname.endsWith('.json'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'vigie-donnees',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 8, maxAgeSeconds: 86400 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Webcam / images distantes : cache d'abord, rafraîchi en arrière-plan
            urlPattern: ({ request }) => request.destination === 'image',
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'vigie-images', expiration: { maxEntries: 20, maxAgeSeconds: 86400 } },
          },
        ],
      },
    }),
  ],
  server: {
    host: true,
    allowedHosts: ['.tbrun.dev'],
    hmr: { clientPort: 443 },
  },
})
