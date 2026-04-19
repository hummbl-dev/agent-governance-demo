"""Tests for the four-mode graduated kill switch."""

import json
import pytest
from agent_governance.kill_switch import KillSwitch, KillSwitchMode, kill_switch_gate


class TestKillSwitchModes:
    def test_starts_disengaged(self):
        ks = KillSwitch()
        assert ks.mode == KillSwitchMode.DISENGAGED

    def test_engage_halt_noncritical(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_NONCRITICAL, "test", "operator")
        assert ks.mode == KillSwitchMode.HALT_NONCRITICAL

    def test_engage_halt_all(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL, "incident", "operator")
        assert ks.mode == KillSwitchMode.HALT_ALL

    def test_engage_emergency(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.EMERGENCY, "critical", "operator")
        assert ks.mode == KillSwitchMode.EMERGENCY

    def test_disengage(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.EMERGENCY, "test", "operator")
        ks.disengage()
        assert ks.mode == KillSwitchMode.DISENGAGED


class TestHaltLogic:
    def test_disengaged_never_halts(self):
        ks = KillSwitch()
        assert not ks.is_halted(critical=False)
        assert not ks.is_halted(critical=True)

    def test_halt_noncritical_blocks_noncritical(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_NONCRITICAL, "test", "op")
        assert ks.is_halted(critical=False)
        assert not ks.is_halted(critical=True)

    def test_halt_all_allows_critical(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL, "test", "op")
        assert ks.is_halted(critical=False)
        assert not ks.is_halted(critical=True)

    def test_emergency_blocks_everything(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.EMERGENCY, "test", "op")
        assert ks.is_halted(critical=False)
        assert ks.is_halted(critical=True)


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "ks.json"
        ks1 = KillSwitch(secret="test-secret", state_path=path)
        ks1.engage(KillSwitchMode.HALT_ALL, "persist test", "admin")
        ks2 = KillSwitch(secret="test-secret", state_path=path)
        assert ks2.mode == KillSwitchMode.HALT_ALL
        assert ks2.state.reason == "persist test"

    def test_tamper_detection(self, tmp_path):
        path = tmp_path / "ks.json"
        ks = KillSwitch(secret="secret", state_path=path)
        ks.engage(KillSwitchMode.EMERGENCY, "test", "admin")
        raw = json.loads(path.read_text())
        raw["sig"] = "tampered"
        path.write_text(json.dumps(raw))
        with pytest.raises(ValueError, match="tampered"):
            KillSwitch(secret="secret", state_path=path)

    def test_wrong_secret_fails(self, tmp_path):
        path = tmp_path / "ks.json"
        KillSwitch(secret="secret-a", state_path=path).engage(
            KillSwitchMode.HALT_ALL, "test", "admin"
        )
        with pytest.raises(ValueError, match="tampered"):
            KillSwitch(secret="secret-b", state_path=path)


class TestGateDecorator:
    def test_gate_allows_when_disengaged(self):
        ks = KillSwitch()

        @kill_switch_gate(ks)
        def my_task():
            return 42

        assert my_task() == 42

    def test_gate_blocks_when_halted(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL, "test", "op")

        @kill_switch_gate(ks)
        def my_task():
            return 42

        with pytest.raises(RuntimeError, match="Kill switch engaged"):
            my_task()

    def test_gate_allows_critical_in_halt_all(self):
        ks = KillSwitch()
        ks.engage(KillSwitchMode.HALT_ALL, "test", "op")

        @kill_switch_gate(ks, critical=True)
        def critical_task():
            return 99

        assert critical_task() == 99
