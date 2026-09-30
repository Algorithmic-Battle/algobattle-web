import { defineConfig, type UserConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { heyApiPlugin } from '@hey-api/vite-plugin';
import { resolve } from 'path'

const baseUrl = new URL(process.env.ALGOBATTLE_BASE_URL ?? "/").pathname.replace(/\/$/, "");

// https://vitejs.dev/config/
const config: UserConfig = {
  base: baseUrl,
  envPrefix: "ALGOBATTLE_",
  plugins: [
    heyApiPlugin({
      config: {
        input: './openapi.json',
        output: './typescript_client',
        plugins: [
            "@hey-api/typescript",
            {
                name: '@hey-api/client-fetch',
                baseUrl: baseUrl,
                throwOnError: true,
            },
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
}

config.server!.proxy![`${baseUrl}/api`] = {
    target: "http://dev-backend:8000",
    rewrite: (path: String) => path.replace(baseUrl, ""),
}

export default defineConfig(config)
