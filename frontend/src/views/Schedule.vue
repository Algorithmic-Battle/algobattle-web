<script setup lang="ts">
import { store, type ModelDict, problemURL } from "@/shared";
import { createSchedule, deleteSchedule as deleteScheduleRequest, editSchedule, getProblems, login, scheduledMatches } from "@client";
import { Modal } from "bootstrap";
import type { ScheduledMatch, Problem, ScheduleAffects } from "@client";
import { computed, onMounted, ref, watch } from "vue";
import { Temporal } from "temporal-polyfill";
import TimePicker from "@/components/TimePicker.vue";

const matches = ref<ModelDict<ScheduledMatch>>({});
const problems = ref<ModelDict<Problem>>({});
const repeatMatch = ref(false);
const repeatOccurrences = ref(2);
const repeatInterval = ref(1);
const repeatIntervalUnit = ref<"minutes" | "hours" | "days" | "weeks">("days");
const affects = ref<ScheduleAffects>("current");
const editData = ref<Partial<ScheduledMatch>>({});
const confirmDelete = ref<boolean>(false);
const affectedSeriesMatches = ref<ScheduledMatch[]>([]);
const affectedMatchesLoading = ref(false);
let affectedMatchesRequest = 0;
const sortedMatches = computed(() => {
  const sorted = Object.values(matches.value);
  sorted.sort((a, b) => Temporal.Instant.compare(a.time, b.time));
  return sorted;
});

const affectedMatches = computed(() => {
  const series = [...affectedSeriesMatches.value].sort((a, b) =>
    Temporal.Instant.compare(a.time, b.time),
  );
  if (affects.value === "following" && editData.value.id) {
    const selectedTime = matches.value[editData.value.id]?.time;
    if (selectedTime) {
      return series.filter((match) => Temporal.Instant.compare(match.time, selectedTime) >= 0);
    }
  }
  return series;
});

watch([affects, () => editData.value.repeats_id], async ([selectedAffects, repeatsId]) => {
  const requestId = ++affectedMatchesRequest;
  affectedSeriesMatches.value = [];
  if (selectedAffects === "current" || !repeatsId) {
    affectedMatchesLoading.value = false;
    return;
  }

  affectedMatchesLoading.value = true;
  try {
    const result = await scheduledMatches({ scheduled_with: repeatsId });
    if (requestId === affectedMatchesRequest) {
      const data = result.data ?? { problems: {}, matches: {} };
      affectedSeriesMatches.value = Object.values(data.matches ?? {});
      problems.value = { ...problems.value, ...(data.problems ?? {}) } as ModelDict<Problem>;
    }
  } finally {
    if (requestId === affectedMatchesRequest) {
      affectedMatchesLoading.value = false;
    }
  }
});

const previewTimes = computed(() => {
  if (!editData.value.time) {
    return [];
  }
  const firstTime = editData.value.time.toZonedDateTimeISO(Temporal.Now.timeZoneId());
  const repeating = !editData.value.id && repeatMatch.value;
  const count = repeating ? repeatOccurrences.value : 1;
  if (
    !Number.isInteger(count) ||
    count < 1 ||
    (repeating && (!Number.isInteger(repeatInterval.value) || repeatInterval.value < 1))
  ) {
    return [];
  }
  return Array.from({ length: count }, (_, index) => {
    const interval = repeating ? index * repeatInterval.value : 0;
    const duration = {
      minutes: { minutes: interval },
      hours: { hours: interval },
      days: { days: interval },
      weeks: { weeks: interval },
    }[repeatIntervalUnit.value];
    return firstTime.add(duration).toLocaleString();
  });
});

let modal: Modal;
onMounted(async () => {
  const results = await scheduledMatches();
  const data = results.data ?? { problems: {}, matches: {} } as any;
  problems.value = (data.problems ?? {}) as ModelDict<Problem>;
  matches.value = (data.matches ?? {}) as ModelDict<ScheduledMatch>;
  modal = Modal.getOrCreateInstance("#editModal");
  if (store.team == "admin") {
    const problemResult = await getProblems({tournament: store.tournament?.id});
    problems.value = (problemResult.data ?? {}) as ModelDict<Problem>;
  }
});

function openModal(match: ScheduledMatch | undefined) {
  editData.value = match
    ? { ...match }
    : { points: 100 };
  repeatMatch.value = false;
  repeatOccurrences.value = 2;
  repeatInterval.value = 1;
  repeatIntervalUnit.value = "days";
  affects.value = "current";
  confirmDelete.value = false;
  modal.show();
}

function intervalAsDuration() {
  switch (repeatIntervalUnit.value) {
    case "minutes":
      return `PT${repeatInterval.value}M`;
    case "hours":
      return `PT${repeatInterval.value}H`;
    case "days":
      return `P${repeatInterval.value}D`;
    case "weeks":
      return `P${repeatInterval.value * 7}D`;
  }
}

async function sendData() {
  console.log("ads")
  if (editData.value.id) {
    const result = await editSchedule({
      id: editData.value.id,
      bodyEditSchedule: {
        time: editData.value.time,
        problem: editData.value.problem,
        points: editData.value.points,
        name: editData.value.name,
        affects: affects.value,
      },
    });
    for (const updatedMatch of result.data ?? []) {
      matches.value[updatedMatch.id] = updatedMatch;
    }
  } else {
    if (
      !editData.value.time ||
      editData.value.problem === undefined ||
      editData.value.points === undefined
    ) {
      console.log("???")
      return;
    }
    const result = await createSchedule({
      bodyCreateSchedule: {
        problem: editData.value.problem,
        time: editData.value.time,
        points: editData.value.points,
        name: editData.value.name ?? "",
        repeats: repeatMatch.value
          ? {
              occurrences: repeatOccurrences.value,
              interval: intervalAsDuration(),
            }
          : null,
      },
    });
    for (const newMatch of result.data ?? []) {
      matches.value[newMatch.id] = newMatch;
    }
  }
  modal.hide();
}
async function deleteMatch() {
  if (editData.value.id) {
    await deleteScheduleRequest({ id: editData.value.id, affects: affects.value });
    const results = await scheduledMatches();
    const data = results.data ?? { problems: {}, matches: {} };
    matches.value = (data.matches ?? {}) as ModelDict<ScheduledMatch>;
    modal.hide();
  }
}
</script>

<template>
  <template v-if="store.tournament">
    <table v-if="sortedMatches.length !== 0" class="table">
      <thead>
        <tr>
          <th scope="col">Name</th>
          <th scope="col">Time</th>
          <th scope="col">Problem</th>
          <th scope="col">Points</th>
          <th v-if="store.team == 'admin'" scope="col"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="match in sortedMatches" :match="match" :key="match.id">
          <td>{{ match.name }}</td>
          <td>{{ match.time.toLocaleString() }}</td>
          <td>
            <RouterLink :to="problemURL(problems[match.problem])">{{ problems[match.problem].name }}</RouterLink>
          </td>
          <td>{{ match.points }}</td>
          <td v-if="store.team == 'admin'" class="text-end">
            <button
              type="button"
              class="btn btn-sm btn-warning"
              title="Edit"
              @click="(e) => openModal(match)"
            >
              <i class="bi bi-pencil"></i>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="alert alert-info" role="alert">
      There aren't any matches scheduled in the {{ store.tournament.name }} tournament yet.
    </div>
    <button
      v-if="store.team == 'admin'"
      type="button"
      class="btn btn-primary btn-sm me-auto"
      @click="(e) => openModal(undefined)"
    >
      Schedule new match
    </button>
  </template>
  <div v-else-if="!store.user" class="alert alert-danger" role="alert">
    You need to log in before you can view the scheduled matches.
  </div>
  <div v-else class="alert alert-danger" role="alert">
    You need to select a team before you can view the scheduled matches.
  </div>

  <div class="modal fade" id="editModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="sendData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
            <span v-if="editData.id">Edit scheduled match</span>
            <span v-else>Schedule new match</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="name" class="form-label">Name</label>
          <input id="name" class="form-control" type="text" maxlength="32" v-model="editData.name" />
          <label for="time" class="form-label">Time</label>
          <TimePicker id="time" step="60" required v-model:time="editData.time" :default-time="new Temporal.PlainTime(23, 59)" />
          <label for="problem" class="form-label">Problem</label>
          <select id="problem" class="form-select" required v-model="editData.problem">
            <option v-for="(problem, id) in problems" :value="id">{{ problem.name }}</option>
          </select>
          <label for="points" class="form-label">Points</label>
          <input id="points" class="form-control" type="number" min="0" required v-model="editData.points" />
          <template v-if="!editData.id">
            <label for="repeatMatch" class="form-label mt-3">Repeat this match?</label>
            <select id="repeatMatch" class="form-select" v-model="repeatMatch">
              <option :value="false">No</option>
              <option :value="true">Yes</option>
            </select>
            <template v-if="repeatMatch">
              <label for="repeatOccurrences" class="form-label mt-3">Number of occurrences</label>
              <input
                id="repeatOccurrences"
                class="form-control"
                type="number"
                min="2"
                step="1"
                required
                v-model.number="repeatOccurrences"
              />
              <label for="repeatInterval" class="form-label mt-3">Interval between matches</label>
              <div class="input-group">
                <input
                  id="repeatInterval"
                  class="form-control"
                  type="number"
                  min="1"
                  step="1"
                  required
                  v-model.number="repeatInterval"
                />
                <select class="form-select" aria-label="Interval unit" v-model="repeatIntervalUnit">
                  <option value="minutes">Minutes</option>
                  <option value="hours">Hours</option>
                  <option value="days">Days</option>
                  <option value="weeks">Weeks</option>
                </select>
              </div>
            </template>
            <div v-if="previewTimes.length > 1" class="mt-3">
              <span class="form-label">Matches will be scheduled at:</span>
              <ol class="mb-0">
                <li v-for="(time, index) in previewTimes" :key="index">{{ time }}</li>
              </ol>
            </div>
          </template>
          <template v-else>
            <label for="affects" class="form-label mt-3">
              {{ confirmDelete ? "Delete" : "Apply changes to" }}
            </label>
            <select id="affects" class="form-select" v-model="affects">
              <option value="current">Only this match</option>
              <option v-if="editData.repeats_id" value="following">This and following matches</option>
              <option v-if="editData.repeats_id" value="all">All matches in the series</option>
            </select>
            <div v-if="affects !== 'current'" class="mt-3" aria-live="polite">
              <div v-if="affectedMatchesLoading" class="text-muted" role="status">
                Loading affected matches...
              </div>
              <template v-else>
                <span class="form-label">
                  {{ confirmDelete ? "Matches that will be deleted:" : "Matches that will be edited:" }}
                </span>
                <ul v-if="affectedMatches.length" class="mb-0">
                  <li v-for="match in affectedMatches" :key="match.id">
                    {{ match.name || "Unnamed match" }} — {{ match.time.toLocaleString() }}
                  </li>
                </ul>
                <div v-else class="text-muted">No matches will be affected.</div>
              </template>
            </div>
          </template>
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
          <button
            v-if="editData.id"
            type="button"
            class="btn btn-danger ms-2"
            @click="confirmDelete ? deleteMatch() : (confirmDelete = true)"
          >
            {{ confirmDelete ? "Confirm deletion" : "Delete match" }}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button v-if="!confirmDelete" type="submit" class="btn btn-primary">
            {{ editData.id ? "Save" : "Schedule" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
