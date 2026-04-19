"""Tests for the append-only governance bus."""

from agent_governance.governance_bus import GovernanceBus


class TestPosting:
    def test_post_creates_entry(self):
        bus = GovernanceBus()
        entry = bus.post("agent-1", "STATUS", "all systems nominal")
        assert entry.agent == "agent-1"
        assert entry.event_type == "STATUS"
        assert entry.message == "all systems nominal"
        assert len(entry.content_hash) == 16

    def test_count_increments(self):
        bus = GovernanceBus()
        assert bus.count == 0
        bus.post("a1", "STATUS", "msg1")
        bus.post("a1", "STATUS", "msg2")
        assert bus.count == 2

    def test_unique_hashes(self):
        bus = GovernanceBus()
        e1 = bus.post("a1", "STATUS", "msg1")
        e2 = bus.post("a1", "STATUS", "msg2")
        assert e1.content_hash != e2.content_hash


class TestQuerying:
    def test_query_all(self):
        bus = GovernanceBus()
        bus.post("a1", "STATUS", "msg1")
        bus.post("a2", "ERROR", "msg2")
        results = bus.query()
        assert len(results) == 2

    def test_query_by_agent(self):
        bus = GovernanceBus()
        bus.post("a1", "STATUS", "msg1")
        bus.post("a2", "ERROR", "msg2")
        bus.post("a1", "COMPLETE", "msg3")
        results = bus.query(agent="a1")
        assert len(results) == 2
        assert all(e.agent == "a1" for e in results)

    def test_query_by_type(self):
        bus = GovernanceBus()
        bus.post("a1", "STATUS", "msg1")
        bus.post("a1", "ERROR", "msg2")
        results = bus.query(event_type="ERROR")
        assert len(results) == 1

    def test_query_limit(self):
        bus = GovernanceBus()
        for i in range(10):
            bus.post("a1", "STATUS", f"msg{i}")
        results = bus.query(limit=3)
        assert len(results) == 3


class TestPersistence:
    def test_save_and_reload(self, tmp_path):
        path = tmp_path / "bus.jsonl"
        bus1 = GovernanceBus(path=path)
        bus1.post("a1", "STATUS", "persisted")
        bus1.post("a2", "ERROR", "also persisted")
        bus2 = GovernanceBus(path=path)
        assert bus2.count == 2
        results = bus2.query(agent="a1")
        assert len(results) == 1
        assert results[0].message == "persisted"

    def test_append_only(self, tmp_path):
        path = tmp_path / "bus.jsonl"
        bus = GovernanceBus(path=path)
        bus.post("a1", "STATUS", "first")
        bus.post("a1", "STATUS", "second")
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
