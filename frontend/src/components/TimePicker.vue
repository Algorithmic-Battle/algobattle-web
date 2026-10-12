<script setup lang="ts">
import { computed, ref, useAttrs, useId, watch } from "vue";
import { Temporal } from "temporal-polyfill";

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    time?: Temporal.Instant | null;
    defaultTime?: "now" | Temporal.PlainTime;
  }>(),
  {
    time: null,
    defaultTime: "now",
  },
);

const emit = defineEmits<{
  "update:time": [time: Temporal.Instant | null];
}>();

const attrs = useAttrs();
const generatedId = useId();
const dateValue = ref("");
const timeValue = ref("");

const inputId = computed(() => (typeof attrs.id === "string" ? attrs.id : generatedId));
const inputName = computed(() => (typeof attrs.name === "string" ? attrs.name : undefined));
const step = computed(() => {
  const value = Number(attrs.step ?? 60);
  return Number.isFinite(value) && value > 0 ? value : 60;
});
const forwardedAttrs = computed(() =>
  Object.fromEntries(
    Object.entries(attrs).filter(([key]) => !["id", "name", "step", "type", "class"].includes(key)),
  ),
);
const combinedValue = computed(() =>
  dateValue.value && timeValue.value ? `${dateValue.value}T${timeValue.value}` : "",
);

watch(
  () => props.time,
  (value) => {
    const localTime = value?.toZonedDateTimeISO(Temporal.Now.timeZoneId());
    dateValue.value = localTime?.toPlainDate().toString() ?? "";
    timeValue.value = localTime?.toPlainTime().toString() ?? "";
  },
  { immediate: true },
);

function defaultPlainTime(): Temporal.PlainTime {
  return props.defaultTime === "now"
    ? Temporal.Now.plainTimeISO().round({ smallestUnit: "minute", roundingMode: "floor" })
    : props.defaultTime;
}

function updateTime() {
  if (!dateValue.value || !timeValue.value) {
    emit("update:time", null);
    return;
  }

  const dateTime = Temporal.PlainDate.from(dateValue.value).toPlainDateTime(
    Temporal.PlainTime.from(timeValue.value),
  );
  emit("update:time", dateTime.toZonedDateTime(Temporal.Now.timeZoneId()).toInstant());
}

function updateDate(event: Event) {
  dateValue.value = (event.target as HTMLInputElement).value;
  if (!dateValue.value) {
    timeValue.value = "";
  } else if (!timeValue.value) {
    timeValue.value = defaultPlainTime().toString();
  }
  updateTime();
}

function updateTimeValue(event: Event) {
  timeValue.value = (event.target as HTMLInputElement).value;
  if (!timeValue.value) {
    dateValue.value = "";
  } else if (!dateValue.value) {
    dateValue.value = Temporal.Now.plainDateISO().toString();
  }
  updateTime();
}
</script>

<template>
  <div class="d-flex gap-2">
    <div class="flex-fill">
      <label class="visually-hidden" :for="inputId">Date</label>
      <input
        v-bind="forwardedAttrs"
        :id="inputId"
        :class="['form-control', attrs.class]"
        type="date"
        :value="dateValue"
        @input="updateDate"
      />
    </div>
    <div class="flex-fill">
      <label class="visually-hidden" :for="`${inputId}-time`">Time</label>
      <input
        v-bind="forwardedAttrs"
        :id="inputId ? `${inputId}-time` : undefined"
        :class="['form-control', attrs.class]"
        type="time"
        :step="step"
        :value="timeValue"
        @input="updateTimeValue"
      />
    </div>
    <input v-if="inputName" type="hidden" :name="inputName" :value="combinedValue" />
  </div>
</template>
