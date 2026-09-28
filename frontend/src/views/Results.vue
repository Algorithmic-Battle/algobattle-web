<script setup lang="ts">
import { store, type ModelDict, formatDateTime, problemURL } from "@/shared";
import {
  addResult,
  createExtraPoints,
  deleteExtraPoints as deleteExtraPointsRequest,
  deleteResults,
  editExtraPoints,
  getExtraPoints,
  getProblems,
  getTeams,
  results as getResults,
  searchProgram,
  type MatchStatus,
  type Role,
  updateResult,
} from "@client";
import { Modal } from "bootstrap";
import type {
  Problem,
  MatchResult,
  Team,
  DbFile,
  ResultParticipant,
  Program,
  ExtraPoints,
} from "@client";
import { computed, onMounted, ref, toRaw, watch } from "vue";
import DownloadButton from "@/components/DownloadButton.vue";
import FileInput from "@/components/FileInput.vue";
import ResultChart from "@/components/ResultChart.vue";
import { DateTime } from "luxon";
import DeleteButton from "@/components/DeleteButton.vue";

const activePage = ref<"results" | "extrapoints">("results");
const problems = ref<ModelDict<Problem>>({});
const resultsData = ref<ModelDict<MatchResult>>({});
const teams = ref<ModelDict<Team>>({});
const programs = ref<{ [key: string]: Program[] }>({});
const chartState = ref(0);
const sortedResults = computed(() => {
  const sorted = Object.values(resultsData.value);
  sorted.sort((a, b) => {
    if (a.time < b.time) {
      return 1;
    } else if (a.time > b.time) {
      return -1;
    } else {
      return 0;
    }
  });
  return sorted;
});

let editModal: Modal;
let detailModal: Modal;
onMounted(async () => {
  const res = await getResults({ tournament: store.tournament?.id });
  const data = res.data ?? { problems: {}, results: {}, teams: {} };
  problems.value = data.problems ?? {};
  resultsData.value = (data.results ?? {}) as ModelDict<MatchResult>;
  teams.value = (data.teams ?? {}) as ModelDict<Team>;
  if (store.team == "admin") {
    var remaining = true;
    var offset = 0;
    while (remaining) {
      const res = await getTeams({ tournament: store.tournament?.id, offset });
      const teamData = res.data ?? { teams: {}, total: 0 };
      teams.value = { ...teams.value, ...(teamData.teams ?? {}) };
      const numResults = Object.keys(teamData.teams ?? {}).length;
      if ((teamData.total ?? 0) > offset + numResults) {
        offset += numResults;
      } else {
        remaining = false;
      }
    }
  }
  programs.value = {};
  Object.values(data.results ?? {})
    .flatMap((r: any) => (r.participants ?? []).flatMap((p: any) => [p.generator, p.solver]))
    .forEach((prog: any) => {
      if (!prog) {
        return;
      }
      const tag = prog.problem + prog.team + prog.role;
      if (tag in programs.value) {
        if (programs.value[tag].findIndex((p) => p.id === prog.id) !== -1) {
          return;
        }
        programs.value[tag].push(prog);
      } else {
        programs.value[tag] = [prog];
      }
    });
  editModal = Modal.getOrCreateInstance("#editModal");
  if (store.team == "admin") {
    const problemResult = await getProblems({
      tournament: store.tournament?.id,
    });
    problems.value = problemResult.data ?? {};
  }
  const extraResult = await getExtraPoints({ tournament: store.tournament?.id });
  extrapoints.value = extraResult.data ?? [];
  detailModal = Modal.getOrCreateInstance("#detailModal");
});

interface EditData {
  id?: string;
  status: MatchStatus;
  time?: string;
  problem?: string;
  logs?: DbFile | null;
  participants: Partial<ResultParticipant>[];
  confirmDelete: boolean;
  newLogs?: File;
}

const editData = ref<EditData>({
  status: "complete",
  participants: [],
  confirmDelete: false,
});

function openEdit(match: MatchResult | undefined) {
  editData.value = match
    ? { ...structuredClone(toRaw(match)), time: match.time.slice(0, 19), confirmDelete: false }
    : {
        status: "complete",
        problem: undefined,
        participants: [],
        confirmDelete: false,
      };
  editModal.show();
}

async function sendData() {
  var res;
  if (editData.value.id) {
    res = await updateResult({
      id: editData.value.id,
      problem: editData.value.problem!,
      status: editData.value.status!,
      time: editData.value.time!,
      teams: editData.value.participants.filter((p) => !!p.team_id).map((p) => p.team_id as string) as any,
      generators: editData.value.participants.filter((p) => !!p.generator?.id).map((p) => p.generator!.id) as any,
      solvers: editData.value.participants.filter((p) => !!p.solver?.id).map((p) => p.solver!.id) as any,
      points: editData.value.participants.map((p) => p.points ?? 0) as any,
      bodyUpdateResult: { logs: editData.value.newLogs },
    });
  } else {
    res = await addResult({
      problem: editData.value.problem!,
      status: editData.value.status!,
      time: editData.value.time!,
      teams: editData.value.participants.filter((p) => !!p.team_id).map((p) => p.team_id as string) as any,
      generators: editData.value.participants.filter((p) => !!p.generator?.id).map((p) => p.generator!.id) as any,
      solvers: editData.value.participants.filter((p) => !!p.solver?.id).map((p) => p.solver!.id) as any,
      points: editData.value.participants.map((p) => p.points ?? 0) as any,
      bodyAddResult: { logs: editData.value.newLogs },
    });
  }
  const resultData = (res.data ?? null) as MatchResult | null;
  if (resultData) {
    resultsData.value[resultData.id] = resultData;
  }
  editModal.hide();
  chartState.value++;
}

async function deleteResult() {
  if (editData.value.id) {
    await deleteResults({
      id: editData.value.id,
    });
    delete resultsData.value[editData.value.id];
    editModal.hide();
    chartState.value++;
  }
}

function getPrograms(team: string, role: Role) {
  if (!editData.value.problem || programs.value[editData.value.problem + team + role]) {
    return;
  }
  programs.value[editData.value.problem + team + role] = [];
  searchProgram({
    team,
    role,
    problem: editData.value.problem,
  }).then((response) => {
    const data = response.data ?? { programs: {} };
    programs.value[editData.value.problem + team + role] = Object.values(data.programs ?? {});
  });
}

function selectProblem() {
  for (const participant of editData.value.participants) {
    if (participant.team_id) {
      getPrograms(participant.team_id, "generator");
      getPrograms(participant.team_id, "solver");
      participant.generator = null;
      participant.solver = null;
    }
  }
}

const detailView = ref<MatchResult>();
const ownParticipant = computed(() => {
  const team = store.team;
  if (!team || team == "admin") {
    return undefined;
  }
  const list = detailView.value?.participants.filter((p) => p.team_id == team.id);
  return list && list.length >= 1 ? list[0] : undefined;
});

function openDetail(result: MatchResult) {
  detailView.value = result;
  detailModal.show();
}

const datetimeStep = computed(() => {
  if (!editData.value.time) {
    return 60;
  }
  return DateTime.fromISO(editData.value.time).second !== 0 ? 1 : 60;
});

const extrapoints = ref<ExtraPoints[]>([]);
const extraEditData = ref<Partial<ExtraPoints> & { freeformTag?: boolean }>({});

async function openExtraEdit(extra: ExtraPoints | undefined) {
  const freeform = tags.value.length === 0;
  extraEditData.value = extra
    ? { ...extra, time: extra.time.slice(0, 19), freeformTag: freeform }
    : { time: DateTime.now().startOf("minute").toISO({ includeOffset: false })!, freeformTag: freeform };
  Modal.getOrCreateInstance("#extraPointsModal").show();
}

async function sendExtraPointsData() {
  if (extraEditData.value.id) {
    const res = await editExtraPoints({
      id: extraEditData.value.id,
      time: extraEditData.value.time,
      tag: extraEditData.value.tag,
      team: extraEditData.value.team?.id,
      points: extraEditData.value.points,
      description: extraEditData.value.description,
    });
    const data = (res.data ?? null) as ExtraPoints | null;
    if (data) {
      const i = extrapoints.value.findIndex((e) => e.id === data.id);
      extrapoints.value[i] = data;
    }
  } else {
    const res = await createExtraPoints({
      time: extraEditData.value.time!,
      team: extraEditData.value.team!.id,
      points: extraEditData.value.points!,
      description: extraEditData.value.description,
      body: extraEditData.value.tag ?? "",
    });
    const data = (res.data ?? null) as ExtraPoints | null;
    if (data) {
      extrapoints.value.push(data);
    }
  }
  Modal.getOrCreateInstance("#extraPointsModal").hide();
  chartState.value++;
}

async function deleteExtraPoints() {
  if (extraEditData.value.id) {
    await deleteExtraPointsRequest({ id: extraEditData.value.id });
    const i = extrapoints.value.findIndex((e) => e.id === extraEditData.value.id);
    extrapoints.value.splice(i, 1);
    Modal.getOrCreateInstance("#extraPointsModal").hide();
    chartState.value++;
  }
}

const tags = computed(() => Array.from(new Set(extrapoints.value.map(e => e.tag))));
function makeFreeform() {
  if (extraEditData.value.tag === null) {
    extraEditData.value.tag = "";
    extraEditData.value.freeformTag = true;
  }
}
</script>

<template>
  <template v-if="store.tournament">
    <h1>Tournament overview</h1>
    <ResultChart :tournament="store.tournament" :state="chartState" id="overallChart" />
    <ul class="nav nav-tabs">
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{ active: activePage === 'results' }"
          :aria-current="activePage === 'results'"
          @click="(e) => (activePage = 'results')"
        >
          Match Results
        </button>
      </li>
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{ active: activePage === 'extrapoints' }"
          :aria-current="activePage === 'extrapoints'"
          @click="(e) => (activePage = 'extrapoints')"
        >
          Extra Points
        </button>
      </li>
    </ul>
    <template v-if="activePage === 'results'">
      <table v-if="sortedResults.length !== 0" class="table">
        <thead>
          <tr>
            <th scope="col">Time</th>
            <th scope="col">Problem</th>
            <th scope="col">Status</th>
            <th scope="col">Details</th>
            <th v-if="store.team == 'admin'" scope="col"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="result in sortedResults" :key="result.id">
            <td>{{ formatDateTime(result.time) }}</td>
            <td>
              <RouterLink v-if="problems[result.problem]" :to="problemURL(problems[result.problem])">{{ problems[result.problem].name }}</RouterLink>
            </td>
            <td>{{ result.status }}</td>
            <td>
              <button type="button" class="btn btn-outline-primary btn-sm" @click="openDetail(result)">
                <i class="bi bi-eye-fill"></i>
              </button>
            </td>
            <td v-if="store.team == 'admin'" class="text-end">
              <button
                type="button"
                class="btn btn-sm btn-warning"
                title="Edit"
                @click="(e) => openEdit(result)"
              >
                <i class="bi bi-pencil"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="alert alert-info" role="alert">
        There aren't any results in the {{ store.tournament.name }} tournament yet.
      </div>
      <button
        v-if="store.team == 'admin'"
        type="button"
        class="btn btn-primary btn-sm me-auto"
        @click="(e) => openEdit(undefined)"
      >
        Add new result
      </button>
    </template>
    <template v-if="activePage === 'extrapoints'">
      <table v-if="extrapoints.length !== 0" class="table">
        <thead>
          <tr>
            <th scope="col">Time</th>
            <th scope="col">Tag</th>
            <th scope="col">Team</th>
            <th scope="col">Points</th>
            <th scope="col">Description</th>
            <th v-if="store.team == 'admin'" scope="col"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="extra in extrapoints" :key="extra.id">
            <td>{{ formatDateTime(extra.time) }}</td>
            <td>{{ extra.tag }}</td>
            <td>{{ extra.team.name }}</td>
            <td>{{ extra.points }}</td>
            <td>{{ extra.description }}</td>
            <td v-if="store.team == 'admin'" class="text-end">
              <button
                type="button"
                class="btn btn-sm btn-warning"
                title="Edit"
                @click="(e) => openExtraEdit(extra)"
              >
                <i class="bi bi-pencil"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="alert alert-info" role="alert">
        There haven't been any extra points distributed in the {{ store.tournament.name }} tournament yet.
      </div>
      <button
        v-if="store.team == 'admin'"
        type="button"
        class="btn btn-primary btn-sm me-auto"
        @click="(e) => openExtraEdit(undefined)"
      >
        Distribute extra points
      </button>
    </template>
  </template>
  <div v-else-if="!store.user" class="alert alert-danger" role="alert">
    You need to log in before you can view the results.
  </div>
  <div v-else class="alert alert-danger" role="alert">
    You need to select a team before you can view the results.
  </div>

  <div class="modal fade" id="editModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-xl">
      <form class="modal-content" @submit.prevent="sendData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
            <span v-if="editData.id">Edit result</span>
            <span v-else>Add new result</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" />
        </div>
        <div class="modal-body">
          <label for="time" class="form-label">Time</label>
          <input
            id="time"
            class="form-control"
            type="datetime-local"
            :step="datetimeStep"
            required
            v-model="editData.time"
          />
          <label for="problem" class="form-label">Problem</label>
          <select id="problem" class="form-select" required v-model="editData.problem" @click="selectProblem">
            <option v-for="(problem, id) in problems" :value="id">{{ problem.name }}</option>
          </select>
          <label for="status" class="form-label">Status</label>
          <select id="status" class="form-select" required v-model="editData.status">
            <option v-for="status in ['running', 'complete', 'failed']" :value="status">
              {{ status }}
            </option>
          </select>
          <label for="logs" class="form-label">Log file</label>
          <FileInput id="logs" v-model="editData.newLogs" accept=".json, application/json" />
          <table class="table">
            <thead>
              <tr>
                <th scope="col">Team</th>
                <th scope="col">Generator</th>
                <th scope="col">Solver</th>
                <th scope="col">Points</th>
                <th scope="col"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="participant in editData.participants">
                <td>
                  <select
                    :id="participant.team_id + 'team'"
                    class="form-select"
                    required
                    v-model="participant.team_id"
                  >
                    <option v-for="(team, id) in teams" :value="id">
                      {{ team.name }}
                    </option>
                  </select>
                </td>
                <td>
                  <select
                    v-if="participant.team_id && editData.problem"
                    :id="participant.team_id + 'gen'"
                    class="form-select"
                    required
                    v-model="participant.generator"
                    @click="getPrograms(participant.team_id, 'generator')"
                  >
                    <option :value="null">None</option>
                    <option
                      v-for="prog in programs[editData.problem + participant.team_id + 'generator']"
                      :value="prog"
                    >
                      {{ `${prog.name}(${formatDateTime(prog.creation_time)})` }}
                    </option>
                  </select>
                </td>
                <td>
                  <select
                    v-if="participant.team_id && editData.problem"
                    :id="participant.team_id + 'gen'"
                    class="form-select"
                    required
                    v-model="participant.solver"
                    @click="getPrograms(participant.team_id, 'solver')"
                  >
                    <option :value="null">None</option>
                    <option
                      v-for="prog in programs[editData.problem + participant.team_id + 'solver']"
                      :value="prog"
                    >
                      {{ `${prog.name}(${formatDateTime(prog.creation_time)})` }}
                    </option>
                  </select>
                </td>
                <td>
                  <template v-if="participant.team_id">
                    <input
                      class="form-control"
                      type="number"
                      step="any"
                      v-model="participant.points"
                      required
                    />
                  </template>
                </td>
                <td>
                  <button
                    type="button"
                    class="btn btn-danger btn-sm"
                    title="Remove"
                    @click="editData.participants.splice(editData.participants.indexOf(participant), 1)"
                  >
                    <i class="bi bi-x-lg"></i>
                  </button>
                </td>
              </tr>
              <tr>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td>
                  <button
                    type="button"
                    class="btn btn-sm btn-success"
                    @click="editData.participants.push({})"
                  >
                    <i class="bi bi-plus-square-dotted"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="modal-footer">
          <button
            v-if="editData.confirmDelete"
            type="button"
            class="btn btn-secondary"
            @click="(e) => (editData.confirmDelete = false)"
          >
            Cancel
          </button>
          <button v-if="editData.id" type="button" class="btn btn-danger ms-2" @click="deleteResult">
            {{ editData.confirmDelete ? "Confirm deletion" : "Delete result" }}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ editData.id ? "Save" : "Add" }}</button>
        </div>
      </form>
    </div>
  </div>

  <div class="modal fade" id="detailModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-l">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Result details</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <template v-if="detailView">
            <table class="table">
              <thead>
                <th scope="col"></th>
                <th scope="col"></th>
              </thead>
              <tbody>
                <tr v-if="ownParticipant?.generator">
                  <td>Generator used</td>
                  <td>
                    <DownloadButton
                      :file="ownParticipant.generator.file"
                      :label="ownParticipant.generator.name"
                    />
                  </td>
                </tr>
                <tr v-if="ownParticipant?.solver">
                  <td>Solver used</td>
                  <td>
                    <DownloadButton :file="ownParticipant.solver.file" :label="ownParticipant.solver.name" />
                  </td>
                </tr>
                <tr v-if="detailView.logs">
                  <td>Log file</td>
                  <td><DownloadButton :file="detailView.logs" /></td>
                </tr>
              </tbody>
            </table>
            <table class="table mt-3">
              <thead>
                <th scope="col">Team</th>
                <th scope="col">Points</th>
              </thead>
              <tbody>
                <tr
                  v-for="participant in detailView.participants"
                  :class="{ 'table-primary': store.team != 'admin' && participant.team_id == store.team?.id }"
                >
                  <td>{{ teams[participant.team_id].name }}</td>
                  <td>{{ participant.points }}</td>
                </tr>
              </tbody>
            </table>
          </template>
        </div>
      </div>
    </div>
  </div>

  <div class="modal fade" id="extraPointsModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="sendExtraPointsData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="extraPointsModalLabel">
            <span v-if="extraEditData.id">Edit Extra Points</span>
            <span v-else>Distribute Extra Points</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="extraTime" class="form-label">Time</label>
          <input
            id="extratime"
            class="form-control"
            type="datetime-local"
            step="60"
            required
            v-model="extraEditData.time"
          />
          <label for="extraTag" class="form-label">Tag</label>
          <input
            v-if="extraEditData.freeformTag"
            id="extraTag"
            class="form-control"
            type="text"
            maxlength="32"
            required
            v-model="extraEditData.tag"
          />
          <select v-else id="extraTag" class="form-select" required v-model="extraEditData.tag" @change="makeFreeform">
            <option v-for="tag in tags" :value="tag">{{ tag }}</option>
            <hr />
            <option :value="null">New tag</option>
          </select>
          <label for="extraTeam" class="form-label">Team</label>
          <select id="extraTeam" class="form-select" required v-model="extraEditData.team">
            <option v-for="team in teams" :value="team" :key="team.id">{{ team.name }}</option>
          </select>
          <label for="extraPoints" class="form-label">Points</label>
          <input
            id="extraPoints"
            class="form-control"
            type="number"
            step="any"
            v-model="extraEditData.points"
            required
          />
          <label for="extraDescription" class="form-label">Description</label>
          <textarea class="form-control" id="extraDescription" v-model="extraEditData.description"></textarea>
        </div>
        <div class="modal-footer">
          <DeleteButton v-if="extraEditData.id" position="before" @delete="deleteExtraPoints" />
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ extraEditData.id ? "Save" : "Create" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style>
#overallChart {
  margin-bottom: 4rem;
}

#extraDescription {
  height: 4rem;
}

.alert {
  margin-top: 1rem;
}
</style>
