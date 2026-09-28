import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { heyApiPlugin } from '@hey-api/vite-plugin';
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  base: "",
  plugins: [
    heyApiPlugin({
      config: {
        input: './openapi.json',
        output: './typescript_client',
        plugins: [
            "@hey-api/typescript",
            '@hey-api/client-fetch',
            {
                name: '@hey-api/sdk',
                paramsStructure: "flat",
                auth: true,
                operations: {
                    strategy: "flat"
                }
            }
        ],
      },
    }),
    vue(),
  ],
  css: {
    preprocessorOptions: {
      scss: {
        silenceDeprecations: [
          "color-functions",
          "global-builtin",
          "import",
          "if-function",
        ],
      },
    },
  },
  resolve: {
    alias: {
      '~bootstrap': resolve("./node_modules/bootstrap"),
      '@': resolve("./src"),
      "@client": resolve("./typescript_client"),
    }
  },
  server: {
    host: "0.0.0.0",
    proxy: {
        "/api": {
            target: "http://dev-backend:8000",
        },
    },
    watch: {
        usePolling: true,
    },
  },
})
