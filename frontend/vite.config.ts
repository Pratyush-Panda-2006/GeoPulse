import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import cesium from 'vite-plugin-cesium'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Type casting to any to handle the TS2349 ESM/CJS interop error
    (cesium as any)()
  ],
})
