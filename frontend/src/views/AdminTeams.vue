<script setup lang="ts">
import HoverBadgeVue from "@/components/HoverBadge.vue";
import { Modal } from "bootstrap";
import { allTournaments, createTeam, deleteTeam as deleteTeamRequest, editTeam, getTeams, searchUsers } from "@client";
import type { Team, Tournament, User } from "@client";
import { store, type ModelDict } from "@/shared";
import { computed, onMounted, ref, toRaw, watch } from "vue";
import Paginator from "@/components/Paginator.vue";

const teams = ref<ModelDict<Team>>({});
const users = ref<ModelDict<User>>({});
const tournaments = ref<ModelDict<Tournament>>({});

const searchData = ref({
  name: "",
  tournament: "",
});
const isFiltered = computed(() => {
  return searchData.value.name != "" || searchData.value.tournament != "";
});
let modal: Modal;
onMounted(async () => {
  const tournamentResult = await allTournaments();
  tournaments.value = (tournamentResult.data ?? {}) as ModelDict<Tournament>;
  modal = Modal.getOrCreateInstance("#teamModal");
  await search();
});
const total = ref(0);
const offset = ref(0);

async function search(offset: number = 0) {
  const result = await getTeams({
    name: searchData.value.name || undefined,
    tournament: searchData.value.tournament || undefined,
    offset,
  });
  const data = result.data ?? { teams: {}, users: {}, total: 0 };
  teams.value = data.teams ?? {};
  users.value = data.users ?? {};
  total.value = data.total ?? 0;
}
watch(offset, search);

async function clearSearch() {
  searchData.value = {
    name: "",
    tournament: "",
  };
  search();
}

const error = ref("");
const editData = ref(emptyTeam());
const userSearchData = ref({
  name: "",
  email: "",
  result: [] as User[],
});
const confirmDelete = ref(false);

function emptyTeam(): Omit<Team, "tournament"> & { tournament: Tournament | null } {
  return {
    id: "",
    name: "",
    tournament: store.tournament ? { ...store.tournament } : null,
    members: [],
  };
}
function openModal(team: Team | undefined) {
  editData.value = team ? structuredClone(toRaw(team)) : emptyTeam();
  confirmDelete.value = false;
  error.value = "";
  userSearchData.value = {
    name: "",
    email: "",
    result: [],
  };
  userSearch();
  modal.show();
}
async function userSearch() {
  const result = await searchUsers({
    name: userSearchData.value.name || undefined,
    email: userSearchData.value.email || undefined,
  });
  const usersData = result.data ?? { users: {} };
  userSearchData.value.result = Object.values(usersData.users ?? {})
    .filter((u) => !editData.value.members.includes(u.id))
    .slice(0, 5);
  for (const user of userSearchData.value.result) {
    users.value[user.id] = user;
  }
}
async function sendData() {
  if (error.value) {
    return;
  }
  try {
    if (editData.value.id) {
      const oldMembers = teams.value[editData.value.id].members;
      const newMembers = editData.value.members.filter((id) => !oldMembers.includes(id));
      const deletedMembers = oldMembers.filter((id) => !editData.value.members.includes(id));
      const updatedTeam = await editTeam({
        id: editData.value.id,
        name: editData.value.name,
        bodyEditTeam: {
          members: Object.fromEntries(
            newMembers.map((id) => [id, "add"]).concat(deletedMembers.map((id) => [id, "remove"]))
          ),
          tournament: editData.value.tournament?.id,
        }
      });
      teams.value[editData.value.id] = (updatedTeam.data ?? teams.value[editData.value.id]) as Team;
    } else {
      const newTeam = await createTeam({ bodyCreateTeam: {
        tournament: editData.value.tournament!.id,
        members: editData.value.members,
        name: editData.value.name,
      }});
      const created = newTeam.data ?? { id: "", name: editData.value.name, tournament: editData.value.tournament ?? null, members: editData.value.members };
      teams.value[created.id] = created as Team;
    }
    modal.hide();
  } catch {
    error.value = "name";
  }
}
async function deleteTeam() {
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    return;
  } else {
    confirmDelete.value = false;
  }
  await deleteTeamRequest({ id: editData.value.id });
  delete teams.value[editData.value.id];
  modal.hide();
}
async function checkName() {
  const result = await getTeams({
    name: editData.value.name,
    tournament: editData.value.tournament?.id,
  });
  const teamData = result.data ?? { teams: {} };
  const teamsList = Object.values(teamData.teams ?? {}).filter((team) => team.name === editData.value.name);
  if (teamsList.length != 0 && teamsList[0].id != editData.value.id) {
    error.value = "name";
  } else {
    error.value = "";
  }
}
</script>

<template>
  <table class="table">
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col">Tournament</th>
        <th scope="col">Members</th>
        <th scope="col"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(team, id) in teams" :team="team" :key="id">
        <td>{{ team.name }}</td>
        <td>{{ team.tournament.name }}</td>
        <td>{{ team.members.map((u) => users[u].name).join(", ") }}</td>
        <td class="text-end">
          <button
            type="button"
            class="btn btn-sm btn-warning"
            title="Edit team"
            @click="(e) => openModal(team)"
          >
            <i class="bi bi-pencil"></i>
          </button>
        </td>
      </tr>
    </tbody>
  </table>

  <div class="d-flex mb-3 pe-2">
    <button type="button" class="btn btn-primary btn-sm me-auto" @click="(e) => openModal(undefined)">
      Create new team
    </button>
    <button
      type="button"
      class="btn btn-primary btn-sm position-relative"
      data-bs-toggle="collapse"
      data-bs-target="#filters"
      aria-expanded="false"
      aria-controls="filters"
    >
      <i class="bi bi-funnel-fill"></i>
      <span
        class="position-absolute top-0 start-100 translate-middle p-2 bg-danger border border-light rounded-circle"
        v-if="isFiltered"
      >
        <span class="visually-hidden">Applied filters</span>
      </span>
    </button>
    <Paginator v-model="offset" :total="total" />
  </div>

  <div class="d-flex justify-content-end">
    <div class="collapse w-xs" id="filters" aria-labelledby="filterHeading">
      <div class="card card-body">
        <div class="row mb-3">
          <div class="col">
            <label for="nameFilter" class="form-label mb-1">Name</label>
            <input class="form-control" id="nameFilter" type="text" v-model="searchData.name" />
          </div>
          <div class="col">
            <label for="tournamentFilter" class="form-label mb-1">Tournament</label>
            <select class="form-select" id="tournamentFilter" v-model="searchData.tournament">
              <option value=""></option>
              <option v-for="(tournament, id) in tournaments" :value="tournament" :key="id">
                {{ tournament.name }}
              </option>
            </select>
          </div>
        </div>
        <div class="row">
          <div class="col text-end align-self-end">
            <button v-if="isFiltered" class="btn btn-secondary me-2" @click="clearSearch">Clear</button>
            <button class="btn btn-primary" @click="(e) => search()">Apply</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div
    class="modal fade"
    id="teamModal"
    tabindex="-1"
    aria-labelledby="modalLabel"
    aria-hidden="true"
    ref="user_modal"
  >
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="sendData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
            <span v-if="editData.id">Edit team</span>
            <span v-else>Create new team</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="name" class="form-label">Name</label>
          <input
            id="name"
            class="form-control"
            type="text"
            v-model="editData.name"
            maxlength="32"
            required
            :class="{ 'is-invalid': error == 'name' }"
            @change="checkName"
          />
          <div class="invalid-feedback">
            Another team with the same name already exists in this tournament
          </div>
          <label for="tournament" class="form-label">Tournament</label>
          <select
            class="form-select"
            id="tournament"
            v-model="editData.tournament"
            :required="editData.id != ''"
            @change="checkName"
          >
            <option
              v-for="(tournament, id) in tournaments"
              :value="tournament"
              :selected="id == editData.tournament?.id"
            >
              {{ tournament.name }}
            </option>
          </select>
          <label for="members" class="form-label mb-0">Members</label>
          <div id="members" class="d-flex flex-row mb-1 members-box">
            <HoverBadgeVue
              v-for="(id, i) in editData.members"
              type="remove"
              @click="() => editData.members.splice(i, 1)"
              >{{ users[id].name }}</HoverBadgeVue
            >
          </div>
          <div class="card mt-2">
            <div class="card-body">
              <h6 class="card-subtitle mb-2">Add user</h6>
              <div class="row mb-2">
                <div class="col">
                  <label for="searchName" class="form-label">Name</label>
                  <input
                    type="text"
                    class="form-control form-control-sm"
                    id="searchName"
                    v-model="userSearchData.name"
                    @input="userSearch"
                  />
                </div>
                <div class="col">
                  <label for="searchEmail" class="form-label">Email</label>
                  <input
                    type="text"
                    class="form-control form-control-sm"
                    id="searchEmail"
                    v-model="userSearchData.email"
                    @input="userSearch"
                  />
                </div>
              </div>
              <div class="d-flex flex-row members-box">
                <HoverBadgeVue
                  v-for="user in userSearchData.result"
                  type="add"
                  @click="() => editData.members.push(user.id)"
                  >{{ user.name }}</HoverBadgeVue
                >
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button
            v-if="confirmDelete"
            type="button"
            class="btn btn-secondary"
            @click="(e) => (confirmDelete = false)"
          >
            Cancel
          </button>
          <button v-if="editData.id" type="button" class="btn btn-danger ms-2" @click="deleteTeam">
            {{ confirmDelete ? "Confirm deletion" : "Delete tournament" }}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ editData.id ? "Save" : "Create" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style>
.members-box {
  min-height: 1.5rem;
}
</style>
