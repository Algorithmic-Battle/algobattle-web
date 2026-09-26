<script setup lang="ts">
import { store, type ModelDict } from "@/shared";
import {
  type Tournament,
  allTournaments,
  editTeamSettings,
  editUserSettings,
  getServerSettings,
  getTeamSettings,
  getUserSettings,
  type ServerSettings,
} from "@client";

type UserSettings = {
  selected_tournament?: Tournament | null;
  [key: string]: any;
};
type TeamSettings = {
  name?: string;
  [key: string]: any;
};
import { onMounted, ref, watch } from "vue";

const serverSettings = ref<ServerSettings>();
const settings = ref<{
  email: string;
  user: UserSettings;
  team_name?: string;
  team?: TeamSettings;
}>();
const state = ref<"plain" | "success" | { name?: boolean; email?: boolean }>("plain");
const tournaments = ref<ModelDict<Tournament>>({});

watch(settings, () => (state.value = "plain"), { deep: true });

onMounted(async () => {
  if (!store.user) {
    return;
  }
  const serverResult = await getServerSettings();
  serverSettings.value = serverResult.data ?? undefined;
  const userResult = await getUserSettings();
  const teamResult = store.team instanceof Object ? await getTeamSettings() : undefined;
  settings.value = {
    email: store.user.email,
    user: (userResult.data ?? {}) as UserSettings,
    team_name: store.team instanceof Object ? store.team.name : undefined,
    team: (teamResult?.data ?? undefined) as TeamSettings | undefined,
  };
  if (store.user?.is_admin) {
    const tournamentResult = await allTournaments();
    tournaments.value = (tournamentResult.data ?? {}) as ModelDict<Tournament>;
  }
});

async function saveEdit() {
  if (!settings.value || !store.user) {
    return;
  }
  try {
    await editUserSettings({
      email: settings.value.email,
      tournament: settings.value.user.selected_tournament?.id,
    });
    state.value = "success";
    store.user.email = settings.value.email;
    store.tournament = settings.value.user.selected_tournament ?? null;
  } catch (error) {
    state.value = {};
    const err = error as { status?: number; body?: { field?: string } };
    if (err.status === 409 && err.body?.field === "email") {
      state.value = { email: true };
    }
  }
  if (settings.value.team_name || settings.value.team) {
    if (!(store.team instanceof Object) || !settings.value.team_name) {
      return;
    }
    try {
      await editTeamSettings({ name: settings.value.team_name });
      store.team.name = settings.value.team_name;
      for (const team of store.user.teams) {
        if (team.id == store.team.id) {
          team.name = settings.value.team_name;
        }
      }
    } catch (error) {
      if (state.value == "success") {
        state.value = {};
      }
      const err = error as { status?: number; body?: { field?: string } };
      if (err.status === 409 && err.body?.field === "name") {
        state.value = { name: true };
      }
    }
  }
}
</script>

<template>
  <template v-if="store.user && settings && serverSettings">
    <h3 class="mt-3">User settings</h3>
    <div v-if="serverSettings.user_change_email" class="mb-3">
      <label for="email" class="form-label">Email address</label>
      <input
        type="email"
        class="form-control mb-0"
        :class="{ 'is-invalid': state instanceof Object && state.email }"
        id="email"
        aria-describedby="emailHelp"
        autocomplete="email"
        v-model="settings.email"
      />
      <div id="emailHelp" class="form-text">Email address used to log in</div>
      <div class="invalid-feedback">This email is already in use</div>
    </div>
    <template v-if="store.user.is_admin">
      <label for="tournament_select" class="form-label">Select tournament</label>
      <select id="tournament_select" class="form-select" v-model="settings.user.selected_tournament">
        <option v-for="(tournament, id) in tournaments" :value="tournament" :key="id">
          {{ tournament.name }}
        </option>
      </select>
    </template>

    <template v-if="settings.team_name && settings.team && store.team instanceof Object">
      <h3 class="mt-5">Team Settings</h3>
      <div v-if="serverSettings.team_change_name" class="mb-3">
        <label for="teamName" class="form-label">Team name</label>
        <input
          type="text"
          class="form-control mb-0"
          :class="{ 'is-invalid': state instanceof Object && state.name }"
          id="teamName"
          aria-describedby="teamNameHelp"
          autocomplete="off"
          v-model="settings.team_name"
        />
        <div id="teamNameHelp" class="form-text">Name of your team, currently {{ store.team.name }}</div>
        <div class="invalid-feedback">Another team already has this name</div>
      </div>
    </template>

    <div id="saveBox">
      <button class="btn btn-primary" id="saveButton" @click="saveEdit">Save changes</button>
      <span v-if="state === 'success'" class="text-success notif">
        <i class="bi bi-check-lg"></i> Successfully saved settings
      </span>
      <div v-else-if="state !== 'plain'" class="text-danger notif">
        <i class="bi bi-x-lg"></i> Couldn't save changes
      </div>
    </div>
  </template>
  <div v-else-if="!store.user" class="alert alert-danger" role="alert">
    You are not logged in so you cannot edit any settings.
  </div>
  <div v-else class="d-flex justify-content-center pt-3">
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
</template>

<style>
#saveBox {
  margin-top: 1.5rem;
  height: 3rem + 2px;
  align-items: center;
  display: block flex;
  flex-direction: row;
}

.notif {
  margin-left: 1rem;
}
</style>
