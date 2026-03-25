"""Four-mode graduated kill switch with HMAC-signed persistent state."""

from __future__ import annotations

import enum
import functools
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


class KillSwitchMode(enum.IntEnum):
    DISENGAGED = 0
    HALT_NONCRITICAL = 1
    HALT_ALL = 2
    EMERGENCY = 3


@dataclass(frozen=True)
class KillSwitchState:
    mode: KillSwitchMode
    engaged_at: float
    reason: str
    engaged_by: str


class KillSwitch:
    def __init__(self, secret: str = "default-secret", state_path: Optional[Path] = None):
        self._secret = secret.encode()
        self._state_path = state_path
        self._state = KillSwitchState(
            mode=KillSwitchMode.DISENGAGED, engaged_at=0.0, reason="", engaged_by=""
        )
        if state_path and state_path.exists():
            self._load()

    @property
    def mode(self) -> KillSwitchMode:
        return self._state.mode

    @property
    def state(self) -> KillSwitchState:
        return self._state

    def engage(self, mode: KillSwitchMode, reason: str, engaged_by: str) -> None:
        self._state = KillSwitchState(
            mode=mode, engaged_at=time.time(), reason=reason, engaged_by=engaged_by
        )
        if self._state_path:
            self._save()

    def disengage(self) -> None:
        self.engage(KillSwitchMode.DISENGAGED, reason="disengaged", engaged_by="system")

    def is_halted(self, critical: bool = False) -> bool:
        if self._state.mode == KillSwitchMode.DISENGAGED:
            return False
        if self._state.mode == KillSwitchMode.EMERGENCY:
            return True
        if self._state.mode == KillSwitchMode.HALT_ALL:
            return not critical
        if self._state.mode == KillSwitchMode.HALT_NONCRITICAL:
            return not critical
        return False

    def _sign(self, data: bytes) -> str:
        return hmac.new(self._secret, data, hashlib.sha256).hexdigest()

    def _save(self) -> None:
        payload = json.dumps({
            "mode": self._state.mode.value,
            "engaged_at": self._state.engaged_at,
            "reason": self._state.reason,
            "engaged_by": self._state.engaged_by,
        }).encode()
        sig = self._sign(payload)
        self._state_path.write_text(json.dumps({"payload": payload.decode(), "sig": sig}))

    def _load(self) -> None:
        raw = json.loads(self._state_path.read_text())
        payload = raw["payload"].encode()
        if not hmac.compare_digest(self._sign(payload), raw["sig"]):
            raise ValueError("Kill switch state tampered — HMAC verification failed")
        data = json.loads(payload)
        self._state = KillSwitchState(
            mode=KillSwitchMode(data["mode"]),
            engaged_at=data["engaged_at"],
            reason=data["reason"],
            engaged_by=data["engaged_by"],
        )


def kill_switch_gate(
    ks: KillSwitch, critical: bool = False
) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if ks.is_halted(critical=critical):
                raise RuntimeError(
                    f"Kill switch engaged ({ks.mode.name}): {ks.state.reason}"
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator
