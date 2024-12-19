import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Membuka akses ke localhost untuk Docker
    port: 5173, // Port default untuk development
    historyApiFallback: true, // Menangani fallback untuk React Router
  },
});