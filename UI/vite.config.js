import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteSingleFile } from 'vite-plugin-singlefile'

// viteSingleFile empaqueta JS, CSS y el JSON de resultados dentro de un único
// dist/index.html, que se abre con doble clic (sin servidor).
export default defineConfig({
  plugins: [vue(), viteSingleFile()],
  base: './',
  json: { stringify: true },
  build: { outDir: 'dist', emptyOutDir: true },
})
