import * as bootstrap from "bootstrap";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { client } from "@client/client.gen";
import { useCookies } from "@vueuse/integrations/useCookies";

import "./assets/styles.scss";
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

const cookies = useCookies();
const token = cookies.get("algobattle_user_token");
client.setConfig({
  headers: {
    "X-User-Token": typeof token === "string" ? token : undefined,
  },
});

const app = createApp(App);

app.use(router);

app.mount("#app");
