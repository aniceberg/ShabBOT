import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import fcSkeleton from "@fullcalendar/react/skeleton.css?inline";
import fcTheme from "@fullcalendar/react/themes/monarch/theme.css?inline";
import fcPalette from "@fullcalendar/react/themes/monarch/palettes/blue.css?inline";
import appCss from "./styles.css?inline";
import { App } from "./App";
import { queryClient, invalidateAll } from "./api";
import { setHass } from "./hass";
import { setTimeZone } from "./format";
import type { ActivityEntry, Hass } from "./types";

// Panels live inside Home Assistant's shadow DOM, where :root matches nothing; scope theme variables to the panel.
const CSS = [fcSkeleton, fcTheme, fcPalette, appCss].join("\n").replaceAll(":root", "shabbot-panel");

/** The <shabbot-panel> element Home Assistant mounts in the sidebar. */
class ShabbotPanel extends HTMLElement {
  private root?: Root;
  private _hass?: Hass;
  private _narrow = false;
  private unsubscribe?: Promise<() => Promise<void>>;

  set hass(hass: Hass) {
    const first = !this._hass;
    this._hass = hass;
    setHass(hass);
    setTimeZone(hass.config.time_zone);
    this.dataset.colorScheme = hass.themes?.darkMode ? "dark" : "light";
    if (first) this.start();
  }

  set narrow(value: boolean) {
    this._narrow = value;
    this.render();
  }

  // HA also sets `route` and `panel`; ShabBOT doesn't need them.
  set route(_v: unknown) {}
  set panel(_v: unknown) {}

  connectedCallback() {
    if (this._hass && !this.root) this.start();
  }

  disconnectedCallback() {
    this.unsubscribe?.then((unsub) => unsub()).catch(() => undefined);
    this.unsubscribe = undefined;
    this.root?.unmount();
    this.root = undefined;
  }

  private start() {
    if (!this.isConnected || this.root) return;
    injectStyles(this);
    this.root = createRoot(this);
    this.render();
    this.unsubscribe = this._hass!.connection.subscribeMessage<{ type: string; entry?: ActivityEntry }>((msg) => {
      if (msg.type === "activity" && msg.entry) {
        queryClient.setQueryData<ActivityEntry[]>(["activity"], (old) => (old ? [msg.entry!, ...old] : old));
        queryClient.invalidateQueries({ queryKey: ["status"] });
      } else {
        invalidateAll();
      }
    }, { type: "shabbot/subscribe" });
  }

  private render() {
    this.root?.render(
      <QueryClientProvider client={queryClient}>
        <App narrow={this._narrow} />
      </QueryClientProvider>,
    );
  }
}

function injectStyles(el: HTMLElement) {
  const root = el.getRootNode() as Document | ShadowRoot;
  const target = root instanceof ShadowRoot ? root : document.head;
  if (target.querySelector("style[data-shabbot]")) return;
  const style = document.createElement("style");
  style.dataset.shabbot = "";
  style.textContent = CSS;
  target.appendChild(style);
}

if (!customElements.get("shabbot-panel")) customElements.define("shabbot-panel", ShabbotPanel);
