import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

/** Short random id for new list items (crypto.randomUUID needs HTTPS, which local HA often isn't). */
export const tempId = () => Math.random().toString(36).slice(2, 14);

export function moveItem<T>(items: T[], from: number, to: number): T[] {
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

/**
 * Drag-to-reorder for a list, using pointer events so it works with a mouse and on touch screens.
 * The grab handle can also be focused and moved with the arrow keys.
 */
export function useReorder<T>(items: T[], onChange: (items: T[]) => void) {
  const rows = useRef<(HTMLElement | null)[]>([]);
  const dragging = useRef<number | null>(null);
  const [active, setActive] = useState<number | null>(null);

  const moveTo = (from: number, to: number) => {
    if (to === from || to < 0 || to >= items.length) return;
    onChange(moveItem(items, from, to));
    dragging.current = dragging.current === null ? null : to;
    setActive((a) => (a === null ? null : to));
  };

  const handle = (i: number) => ({
    onPointerDown: (e: PointerEvent<HTMLElement>) => {
      if (e.button !== 0) return;
      e.preventDefault(); // no text selection while dragging…
      e.currentTarget.focus(); // …but keep the handle focusable, so arrow keys work after a click
      e.currentTarget.setPointerCapture(e.pointerId);
      dragging.current = i;
      setActive(i);
    },
    onPointerMove: (e: PointerEvent<HTMLElement>) => {
      const from = dragging.current;
      if (from === null) return;
      // New position = how many other rows have their middle above the pointer.
      let to = 0;
      rows.current.forEach((el, k) => {
        if (!el || k === from) return;
        const r = el.getBoundingClientRect();
        if (e.clientY > r.top + r.height / 2) to++;
      });
      moveTo(from, to);
    },
    onPointerUp: () => {
      dragging.current = null;
      setActive(null);
    },
    onPointerCancel: () => {
      dragging.current = null;
      setActive(null);
    },
    onKeyDown: (e: KeyboardEvent<HTMLElement>) => {
      if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
      e.preventDefault();
      const target = e.currentTarget;
      moveTo(i, i + (e.key === "ArrowUp" ? -1 : 1));
      requestAnimationFrame(() => target.focus());
    },
  });

  const row = (i: number) => ({
    ref: (el: HTMLElement | null) => {
      rows.current[i] = el;
    },
    "data-dragging": active === i ? "" : undefined,
  });

  return { handle, row, dragging: active !== null };
}

/** The ⋮⋮ grab handle shown at the start of a reorderable row. */
export function DragHandle(props: ReturnType<ReturnType<typeof useReorder>["handle"]> & { label?: string }) {
  const { label = "Drag to reorder (or focus and use the arrow keys)", ...handlers } = props;
  return (
    <button type="button" className="sb-grip" aria-label={label} title={label} {...handlers}>
      <svg width="14" height="18" viewBox="0 0 14 18" aria-hidden="true" fill="currentColor">
        {[3, 9, 15].flatMap((y) => [4, 10].map((x) => <circle key={`${x}-${y}`} cx={x} cy={y} r="1.6" />))}
      </svg>
    </button>
  );
}
