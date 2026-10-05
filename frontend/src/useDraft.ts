import { useEffect, useRef, useState } from "react";

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/**
 * Local editable copy of server data. If the server copy changes (e.g. from Home Assistant or another
 * browser) while there are no unsaved edits, the draft follows it; unsaved edits are never overwritten.
 */
export function useDraft<T>(source: T | undefined): [T | undefined, (v: T) => void, boolean, () => void] {
  const [draft, setDraft] = useState<T | undefined>(source === undefined ? undefined : structuredClone(source));
  const base = useRef<T | undefined>(source);
  useEffect(() => {
    if (source === undefined) return;
    setDraft((d) => (d === undefined || same(d, base.current) ? structuredClone(source) : d));
    base.current = source;
  }, [source]);
  const dirty = draft !== undefined && source !== undefined && !same(draft, source);
  const reset = () => source !== undefined && setDraft(structuredClone(source));
  return [draft, setDraft as (v: T) => void, dirty, reset];
}
