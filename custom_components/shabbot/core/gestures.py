"""Override gesture detection, independent of Home Assistant.

Detectors (per device, see DeviceConfig "override"):

- event:        a bus event matching a stored matcher starts/ends the override.
                Presets: Zooz/Z-Wave central scene ("zwave_js_value_notification"
                with value "KeyPressed3x"), or anything captured with Learn.
- flip_pattern: N manual state transitions within T seconds (Caséta, Kasa, Wemo...).
- persistence:  the device is manually moved off its protected state N times
                within T seconds, i.e. someone keeps undoing ShabBOT's reverts.
- none:         only the panel / shabbot.start_override service.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

ZWAVE_EVENT = "zwave_js_value_notification"
CENTRAL_SCENE_CC = 91

START = "start"
END = "end"


def zwave_multitap_matchers(device_id: str, taps: int = 3, up_scene: str = "001",
                            down_scene: str = "002") -> dict[str, dict[str, Any]]:
    """Matchers for Z-Wave Central Scene multi-tap (Zooz ZEN7x: scene 001 = up paddle, 002 = down)."""
    value = "KeyPressed" if taps == 1 else f"KeyPressed{taps}x"
    base = {"event_type": ZWAVE_EVENT, "data": {"device_id": device_id, "command_class": CENTRAL_SCENE_CC}}
    return {
        START: {**base, "data": {**base["data"], "property_key": up_scene, "value": value}},
        END: {**base, "data": {**base["data"], "property_key": down_scene, "value": value}},
    }


def event_matches(matcher: dict[str, Any] | None, event_type: str, data: dict[str, Any]) -> bool:
    """True if every key in matcher["data"] equals the event's value (string-compared)."""
    if not matcher or matcher.get("event_type") != event_type:
        return False
    for key, want in (matcher.get("data") or {}).items():
        if key not in data or str(data[key]) != str(want):
            return False
    return True


def suggest_matcher(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build a matcher from a captured event, keeping only identifying keys."""
    keep = ("device_id", "entity_id", "node_id", "command_class", "property_key", "property", "value",
            "button_number", "button_type", "action", "action_type", "leap_button_number", "serial",
            "command", "subtype", "type", "unique_id", "id", "event")
    return {"event_type": event_type, "data": {k: v for k, v in data.items() if k in keep and v is not None}}


@dataclass(slots=True)
class GestureTracker:
    """Tracks manual (non-ShabBOT) state changes for one entity."""

    detector: str = "none"
    count: int = 3
    window: timedelta = timedelta(seconds=6)
    _manual: deque[datetime] = field(default_factory=lambda: deque(maxlen=20))
    _deviations: deque[datetime] = field(default_factory=lambda: deque(maxlen=20))

    @classmethod
    def from_config(cls, override_cfg: dict[str, Any]) -> GestureTracker:
        detector = override_cfg.get("detector", "none")
        defaults = {"flip_pattern": (3, 6), "persistence": (3, 120)}.get(detector, (3, 6))
        return cls(
            detector=detector,
            count=int(override_cfg.get("count") or defaults[0]),
            window=timedelta(seconds=float(override_cfg.get("window_s") or defaults[1])),
        )

    @property
    def needs_extended_grace(self) -> bool:
        """flip_pattern needs reverts held off until the gesture window closes."""
        return self.detector == "flip_pattern"

    def _count_recent(self, q: deque[datetime], now: datetime) -> int:
        while q and now - q[0] > self.window:
            q.popleft()
        return len(q)

    def manual_change(self, now: datetime, deviates: bool) -> bool:
        """Record a manual state change. Returns True if it completes an override gesture.

        `deviates` is True when the new state differs from the protected state.
        """
        if self.detector == "flip_pattern":
            self._manual.append(now)
            if self._count_recent(self._manual, now) >= self.count:
                self._manual.clear()
                return True
        elif self.detector == "persistence" and deviates:
            self._deviations.append(now)
            if self._count_recent(self._deviations, now) >= self.count:
                self._deviations.clear()
                return True
        return False

    def reset(self) -> None:
        self._manual.clear()
        self._deviations.clear()
