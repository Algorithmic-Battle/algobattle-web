import { reactive } from "vue";
import type { UserLogin, Team, Tournament, ServerSettings, Problem } from "@client";
import { Temporal } from "temporal-polyfill";

export type ModelDict<T> = { [key: string]: T };

export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

export const store = reactive<{
  user: UserLogin | null;
  team: Team | "admin" | null;
  tournament: Tournament | null;
  serverSettings?: ServerSettings;
}>({
  user: null,
  team: null,
  tournament: null,
});

export function formatDateTime(time: Temporal.Instant | Temporal.ZonedDateTime): string {
  const instant = time instanceof Temporal.Instant ? time : time.toInstant();
  return instant.toLocaleString("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: Temporal.Now.timeZoneId(),
  });
}

export function deepCopy<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj))
}


export function problemURL(problem: Problem): string {
  const tournamentStr = encodeURIComponent(problem.tournament.name);
  const name = encodeURIComponent(problem.name);
  return `/problems/${tournamentStr}/${name}`;
}

export function toLocalDateTimeInput(value: Temporal.Instant | null | undefined): string {
  return value
    ? value
        .toZonedDateTimeISO(Temporal.Now.timeZoneId())
        .toPlainDateTime()
        .toString({ smallestUnit: "minute" })
    : "";
}

export function fromLocalDateTimeInput(value: string): Temporal.Instant {
  return Temporal.PlainDateTime.from(value).toZonedDateTime(Temporal.Now.timeZoneId()).toInstant();
}

export const baseUrl = import.meta.env.BASE_URL;
