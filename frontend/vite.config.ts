import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // GitHub Pages project sites are served under /<repo-name>/, not /.
  // Routing itself doesn't need this (App.tsx uses HashRouter), but
  // asset URLs (JS/CSS bundle paths) do, or the deployed page loads a
  // blank screen looking for assets at the wrong path. Set
  // VITE_BASE_PATH="/<repo-name>/" as a build-time env var in the
  // GitHub Actions workflow (see .github/workflows/deploy-pages.yml);
  // local dev and any non-GitHub-Pages host can leave it unset.
  base: process.env.VITE_BASE_PATH || '/',
})
