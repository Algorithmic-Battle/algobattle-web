<script setup lang="ts">
import { RouterView, useRouter } from "vue-router";
import PageNavbarIcon from "./components/HomeNavbarIcon.vue";
import { store, baseUrl } from "@/shared";
import { type Team, editUserSettings, getSelf, getServerSettings, getToken } from "@client";
import LoginPane from "./components/LoginPane.vue";
import { useCookies } from "@vueuse/integrations/useCookies";
import { computed, onMounted, watch } from "vue";
import { Dropdown } from "bootstrap";
import { client } from "@client/client.gen";

const router = useRouter();
const cookies = useCookies();

const queryToken = computed(() => {
  let token = router.currentRoute.value.query.login_token;
  if (token instanceof Array) {
    token = token[0];
  }
  return token;
});
watch(queryToken, async (newToken) => {
  if (newToken) {
    let result;
    try {
      result = (await getToken({ login_token: newToken })).data;
    } catch {
      return;
    }
    cookies.set("algobattle_user_token", result.token, {
      expires: new Date(result.expires),
    });
    client.setConfig({
      headers: { "X-User-Token": result.token },
    });
    router.replace({ path: router.currentRoute.value.path });
  }
});

const userToken = computed(() => {
  return cookies.get("algobattle_user_token");
});
watch(
  userToken,
  async (userToken) => {
    const token = typeof userToken === "string" ? userToken : undefined;
    client.setConfig({ headers: { "X-User-Token": token } });
    if (token) {
      try {
        const response = await getSelf();
        store.user = response.data.user;
        store.team = response.data.team;
        store.tournament = response.data.tournament;
      } catch {}
      return;
    }
    store.user = null;
  },
  { immediate: true },
);

async function logout() {
  Dropdown.getOrCreateInstance("#loggedInDropdown").hide();
  cookies.remove("algobattle_user_token");
  client.setConfig({ headers: { "X-User-Token": undefined } });
  router.go(0);
}

async function selectTeam(team: Team | "admin") {
  if (team == "admin" && !store.user?.is_admin) {
    return;
  }
  await editUserSettings({ bodyEditUserSettings: { team: team == "admin" ? "admin" : team.id } });
  router.go(0);
}

const displayName = computed(() => {
  if (!store.user) {
    return "Log in";
  } else if (!store.team) {
    return "No team";
  } else if (store.team == "admin") {
    return "Admin";
  } else {
    return store.team.name;
  }
});

onMounted(async () => {
  try {
    const result = await getServerSettings();
    store.serverSettings = result.data;
  } catch {
    store.serverSettings = undefined;
  }
});
</script>

<template>
  <nav class="navbar navbar-expand-md sticky-top bg-primary-subtle" data-bs-theme="dark">
    <div class="container-xxl">
      <RouterLink to="/" class="navbar-brand">
        <span class="fs-4">Algobattle</span>
      </RouterLink>
      <button
        class="navbar-toggler"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#navbarSupportedContent"
        aria-controls="navbarSupportedContent"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0 nav nav-pills">
          <template v-if="store.tournament">
            <PageNavbarIcon link="/problems" icon="boxes">Problems</PageNavbarIcon>
            <PageNavbarIcon link="/programs" icon="file-earmark-code">Programs</PageNavbarIcon>
            <PageNavbarIcon link="/schedule" icon="calendar-week">Schedule</PageNavbarIcon>
            <PageNavbarIcon link="/results" icon="bar-chart-line">Results</PageNavbarIcon>
          </template>
          <PageNavbarIcon v-if="store.team == 'admin'" link="/admin" icon="people"
            >Admin panel</PageNavbarIcon
          >
          <li class="nav-item mx-2">
            <a :href="baseUrl + '/docs/tutorial/'" class="nav-link align-middle"
              ><i class="me-1 bi bi-book" />User Guide</a
            >
          </li>
        </ul>

        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle text-white"
            href="#"
            role="button"
            data-bs-toggle="dropdown"
            data-bs-auto-close="outside"
            aria-expanded="false"
          >
            <i class="bi bi-person-circle me-2"></i> <strong>{{ displayName }}</strong>
          </a>
          <ul v-if="store.user" class="dropdown-menu" id="loggedInDropdown">
            <li>
              <RouterLink class="dropdown-item" :to="{ name: 'settings' }">Settings</RouterLink>
            </li>
            <template v-if="store.user.teams.length >= (store.user.is_admin ? 1 : 2)">
              <li><hr class="dropdown-divider" /></li>
              <li class="dropdown-header">View as</li>
              <li v-for="team in store.user.teams">
                <button
                  class="dropdown-item"
                  :class="{ active: store.team != 'admin' && store.team?.id == team.id }"
                  @click="selectTeam(team)"
                >
                  {{ team.name }}
                </button>
              </li>
              <li v-if="store.user.is_admin">
                <button
                  class="dropdown-item"
                  :class="{ active: store.team == 'admin' }"
                  @click="selectTeam('admin')"
                >
                  Admin
                </button>
              </li>
            </template>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <button class="dropdown-item" @click="logout">Log out</button>
            </li>
          </ul>
          <LoginPane v-else />
        </div>
      </div>
    </div>
  </nav>

  <div class="container-xxl p-5">
    <RouterView />
  </div>
</template>
