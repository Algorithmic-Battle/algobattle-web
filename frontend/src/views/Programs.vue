<script setup lang="ts">
import {
  type Role,
  deleteProgram as deleteProgramRequest,
  getProblems,
  searchProgram,
  uploadProgram as uploadProgramRequest,
  getSelectedPrograms,
  selectProgram,
} from "@client";
import { formatDateTime, store, type ModelDict } from "@/shared";
import { Modal } from "bootstrap";
import type { Problem, Program, Team } from "@client";
import { computed, onMounted, ref, watch } from "vue";
import FileInput from "@/components/FileInput.vue";
import Paginator from "@/components/Paginator.vue";
import DeleteButton from "@/components/DeleteButton.vue";
import { Temporal } from "temporal-polyfill";

const programs = ref<ModelDict<Program>>({});
const sortedPrograms = computed(() => {
  const sorted = Object.values(programs.value);
  sorted.sort((a, b) => {
    const startA = problems.value[a.problem].start || "";
    const startB = problems.value[b.problem].start || "";
    return (
      (startA && startB
        ? -Temporal.Instant.compare(startA, startB)
        : startA
          ? -1
          : startB
            ? 1
            : 0) ||
      a.role.localeCompare(b.role) ||
      -Temporal.Instant.compare(a.creation_time, b.creation_time)
    );
  });
  return sorted;
});
const problems = ref<ModelDict<Problem>>({});
const teams = ref<ModelDict<Team>>({});
const total = ref(0);
const offset = ref(0);
const selectedPrograms = ref<{[key: string]: boolean}>({});
const searchData = ref({
  name: null,
  team: null,
  role: null,
});
const activeProblems = computed(() => {
  const now = Temporal.Now.instant();
  const probs = Object.values(problems.value).filter(
    (p) =>
      (!p.start || Temporal.Instant.compare(p.start, now) <= 0) &&
      (!p.end || Temporal.Instant.compare(p.end, now) > 0)
  );
  if (probs.length == 1) {
    newProgData.value.problem = probs[0].id;
  }
  return probs;
});

async function search(offset: number = 0) {
  const ret = await searchProgram({ tournament: store.tournament?.id, offset });
  const data = ret.data ?? { programs: {}, problems: {}, teams: {}, total: 0 };
  if (store.team === "admin") {
    problems.value = data.problems ?? {};
  } else {
    const problemResult = await getProblems({ tournament: store.tournament?.id });
    problems.value = problemResult.data ?? {};
  }
  programs.value = data.programs ?? {};
  teams.value = data.teams ?? {};
  total.value = data.total ?? 0;
}
watch(offset, search);

const newProgData = ref<{
  name?: string;
  role?: Role;
  problem?: string;
  file?: File;
  selected?: boolean;
}>({
  name: "",
  selected: true,
});
let modal: Modal;
async function openModal() {
  newProgData.value = {
    name: "",
    selected: true,
  };
  modal.show();
}

async function uploadProgram() {
  if (
    !newProgData.value.file ||
    newProgData.value.file.size == 0 ||
    !newProgData.value.problem ||
    !newProgData.value.role
  ) {
    return;
  }
  const res = (await uploadProgramRequest({
    name: newProgData.value.name,
    role: newProgData.value.role,
    problem: newProgData.value.problem,
    selected: newProgData.value.selected,
    bodyUploadProgram: { file: newProgData.value.file },
  })).data;
  programs.value[res.new.id] = res.new;
  if (newProgData.value.selected) {
    selectedPrograms.value[res.new.id] = true;
  }
  if (res.unselected) {
    delete selectedPrograms.value[res.unselected.id];
  }
  modal.hide();
}

async function deleteProgram(program: Program) {
  await deleteProgramRequest({ id: program.id });
  delete programs.value[program.id];
}

async function selProgram(program: Program) {
  const selected = (await selectProgram({ program: program.id })).data;
  if (selected.unselected) {
    delete selectedPrograms.value[selected.unselected.id];
  }
  selectedPrograms.value[selected.new.id] = true;
}

onMounted(async () => {
  await search();
  const selected =(await getSelectedPrograms()).data ?? [];
  selectedPrograms.value = Object.fromEntries(selected.flatMap((p) => [[p.generator, true], [p.solver, true]]));
  modal = Modal.getOrCreateInstance("#uploadProgram");
});
</script>

<template>
  <template v-if="store.tournament">
    <table v-if="sortedPrograms.length !== 0" class="table table-hover mb-2" id="programs">
      <thead>
        <tr>
          <th scope="col">Problem</th>
          <th scope="col" v-if="store.team == 'admin'">Team</th>
          <th scope="col">Role</th>
          <th scope="col">Uploaded</th>
          <th scope="col">Name</th>
          <th scope="col">File</th>
          <th scope="col"></th>
          <th scope="col"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="program in sortedPrograms" :key="program.id" :class="{ 'table-success': selectedPrograms[program.id] }">
          <td>{{ problems[program.problem].name }}</td>
          <td v-if="store.team == 'admin'">{{ teams[program.team].name }}</td>
          <td>{{ program.role }}</td>
          <td>{{ formatDateTime(program.creation_time) }}</td>
          <td>{{ program.name }}</td>
          <td>
            <a
              role="button"
              class="btn btn-primary btn-sm"
              :href="program.file.location"
              title="Download program file"
              >Download <i class="bi bi-download ms-1"></i
            ></a>
          </td>
          <td class="text-end">
            <span v-if="selectedPrograms[program.id]" class="badge bg-success mb-0">
              Selected
            </span>
            <button
              v-else-if="store.team !== 'admin' && activeProblems.some((p) => p.id === program.problem)"
              type="button"
              class="btn btn-outline-success btn-sm"
              @click="selProgram(program)"
            >
              Select
            </button>
          </td>
          <td class="text-end">
            <DeleteButton
              v-if="store.team === 'admin' || program.user_editable"
              class="btn-sm"
              position="after"
              @delete="deleteProgram(program)"
            />
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="alert alert-info" role="alert">There aren't any programs uploaded already.</div>

    <div class="d-flex mb-3 pe-2">
      <button
        v-if="store.team !== 'admin' && activeProblems.length >= 1"
        type="button"
        class="btn btn-primary btn-sm me-auto"
        @click="openModal"
      >
        Upload new program
      </button>
      <Paginator v-model="offset" :total="total" />
    </div>
  </template>
  <div v-else-if="!store.user" class="alert alert-danger" role="alert">
    You need to log in before you can view the programs.
  </div>
  <div v-else class="alert alert-danger" role="alert">
    You need to select a team before you can view your teams programs.
  </div>

  <div class="modal fade" id="uploadProgram" tabindex="-1" aria-labelledby="docLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
      <form class="modal-content" @submit.prevent="uploadProgram">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="docLabel">Upload program</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body row">
          <div class="col-md-6">
            <div class="mb-3">
              <label for="problem_sel" class="form-label">Problem</label>
              <select
                v-if="activeProblems.length >= 0"
                class="form-select"
                id="problem_sel"
                name="problem"
                required
                v-model="newProgData.problem"
              >
                <option v-for="problem in activeProblems" :value="problem.id">{{ problem.name }}</option>
              </select>
              <span v-else-if="activeProblems[0]" if="problem_sel">{{ activeProblems[0].name }}</span>
              <span v-else>No active problems available</span>
            </div>
            <div class="mb-3">
              <label for="prog_name" class="form-label">Name</label>
              <input
                type="text"
                class="form-control"
                name="name"
                id="prog_name"
                v-model="newProgData.name"
                maxlength="32"
              />
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="role_sel" class="form-label">Role</label>
              <select class="form-select" id="role_sel" name="role" required v-model="newProgData.role">
                <option value="generator">Generator</option>
                <option value="solver">Solver</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="file_select" class="form-label mt-3">Select new program file</label>
              <FileInput id="file_select" v-model="newProgData.file" accept=".prog" required />
            </div>
            <div class="form-check mb-3">
              <input
                id="selected"
                v-model="newProgData.selected"
                class="form-check-input"
                type="checkbox"
              />
              <label class="form-check-label" for="selected">
                Select this program for {{ newProgData.problem ? problems[newProgData.problem]?.name : "the selected problem" }}
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">Upload</button>
        </div>
      </form>
    </div>
  </div>
</template>
