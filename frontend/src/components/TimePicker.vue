<script setup lang="ts">
import { computed, ref, useAttrs, useId, watch } from "vue";
import { Temporal } from "temporal-polyfill";
import { fromLocalDateTimeInput, toLocalDateTimeInput } from "@/shared";

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
const inputValue = ref("");
const inputId = computed(() => (typeof attrs.id === "string" ? attrs.id : generatedId));
const inputClass = computed(() => ["form-control", attrs.class]);
const step = computed(() => {
  const value = Number(attrs.step ?? 60);
  return Number.isFinite(value) && value > 0 ? value : 60;
});
const forwardedAttrs = computed(() =>
  Object.fromEntries(
    Object.entries(attrs).filter(([key]) => !["id", "class", "step", "type"].includes(key)),
  ),
);

watch(
  () => props.time,
  (value) => {
    inputValue.value = toLocalDateTimeInput(value);
  },
  { immediate: true },
);

function defaultPlainTime(): Temporal.PlainTime {
  return props.defaultTime === "now"
    ? Temporal.Now.instant()
        .toZonedDateTimeISO(Temporal.Now.timeZoneId())
        .toPlainTime()
        .round({ smallestUnit: "minute", roundingMode: "floor" })
    : props.defaultTime;
}

function updateTime(event: Event) {
  const value = (event.target as HTMLInputElement).value;
  inputValue.value = value;

  if (!value) {
    emit("update:time", null);
    return;
  }

  let localDateTime = Temporal.PlainDateTime.from(value);
  if (
    !props.time &&
    localDateTime.toPlainTime().equals(Temporal.PlainTime.from("00:00"))
  ) {
    localDateTime = localDateTime.withPlainTime(defaultPlainTime());
    inputValue.value = localDateTime.toString({ smallestUnit: "minute" });
  }

  emit("update:time", fromLocalDateTimeInput(localDateTime.toString()));
}
</script>

<template>
  <div>
    <label class="visually-hidden" :for="inputId">Date and time</label>
    <input
      v-bind="forwardedAttrs"
      :id="inputId"
      :class="inputClass"
      type="datetime-local"
      :step="step"
      :value="inputValue"
      @input="updateTime"
    />
  </div>
</template>
