import { reactive } from "vue";
import type { UserLogin, Team, Tournament, ServerSettings, Problem } from "@client";
import { DateTime } from "luxon";

export type ModelDict<T> = { [key: string]: T };

export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

export function formatDateTime(datetime: string): string {
  return DateTime.fromISO(datetime).toLocaleString(DateTime.DATETIME_SHORT);
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

export function problemURL(problem: Problem): string {
  const tournamentStr = encodeURIComponent(problem.tournament.name);
  const name = encodeURIComponent(problem.name);
  return `/problems/${tournamentStr}/${name}`;
}
