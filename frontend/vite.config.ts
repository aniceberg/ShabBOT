import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Builds one ES module that Home Assistant loads as the sidebar panel.
export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir: "../custom_components/shabbot/frontend",
    emptyOutDir: true,
    target: "es2022",
    cssCodeSplit: false,
    lib: { entry: "src/main.tsx", formats: ["es"], fileName: () => "shabbot-panel.js" },
    minify: true,
    rolldownOptions: { output: { codeSplitting: false, minify: true } },
  },
});
