import { useRef, useSyncExternalStore } from "react";
import type { Hass } from "./types";

// Home Assistant replaces the `hass` object on every state change in the house.
// Keep the latest one here and let components subscribe to just the slice they need.
let current: Hass | undefined;
const listeners = new Set<() => void>();

export function setHass(hass: Hass): void {
  current = hass;
  listeners.forEach((l) => l());
}

export function getHass(): Hass {
  if (!current) throw new Error("hass not ready");
  return current;
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

/** Re-render only when the selected value changes (compared with `isEqual`). */
export function useHassSelector<T>(select: (hass: Hass) => T, isEqual: (a: T, b: T) => boolean = Object.is): T {
  const cache = useRef<{ hass: Hass; value: T } | undefined>(undefined);
  const getSnapshot = () => {
    const hass = getHass();
    const cached = cache.current;
    if (cached && cached.hass === hass) return cached.value;
    const value = select(hass);
    if (cached && isEqual(cached.value, value)) {
      cache.current = { hass, value: cached.value };
      return cached.value;
    }
    cache.current = { hass, value };
    return value;
  };
  return useSyncExternalStore(subscribe, getSnapshot);
}

export const shallowEqual = <T,>(a: T, b: T): boolean => {
  if (Object.is(a, b)) return true;
  if (typeof a !== "object" || typeof b !== "object" || !a || !b) return false;
  const ka = Object.keys(a as object);
  if (ka.length !== Object.keys(b as object).length) return false;
  return ka.every((k) => Object.is((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k]));
};

export function callWS<T>(msg: Record<string, unknown>): Promise<T> {
  return getHass().callWS<T>(msg);
}

export function friendlyName(entityId: string): string {
  const st = current?.states[entityId];
  return (st?.attributes.friendly_name as string | undefined) ?? entityId;
}

/** Controllable entity domains offered in pickers. */
export const CONTROLLABLE = ["light", "switch", "input_boolean", "fan", "climate", "cover", "media_player", "water_heater"];
