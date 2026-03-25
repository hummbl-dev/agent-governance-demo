"""Tests for HMAC-SHA256 signed delegation tokens."""

import time
import pytest
from agent_governance.delegation_token import DelegationToken, TokenAuthority


class TestTokenIssuance:
    def test_issue_token(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "agent-1", {"read", "write"}, {"repo"})
        assert token.issuer == "admin"
        assert token.subject == "agent-1"
        assert "read" in token.permitted_operations
        assert "write" in token.permitted_operations
        assert "repo" in token.resources

    def test_token_has_signature(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "agent-1", {"read"}, {"repo"})
        assert len(token.signature) == 64

    def test_token_has_unique_id(self):
        ta = TokenAuthority()
        t1 = ta.issue("admin", "a1", {"read"}, {"repo"})
        t2 = ta.issue("admin", "a2", {"read"}, {"repo"})
        assert t1.token_id != t2.token_id


class TestTokenVerification:
    def test_valid_token_verifies(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "agent-1", {"read"}, {"repo"}, ttl_seconds=60)
        assert ta.verify(token)

    def test_wrong_secret_fails(self):
        ta1 = TokenAuthority(secret="secret-a")
        ta2 = TokenAuthority(secret="secret-b")
        token = ta1.issue("admin", "agent-1", {"read"}, {"repo"})
        assert not ta2.verify(token)

    def test_expired_token_fails(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "agent-1", {"read"}, {"repo"}, ttl_seconds=0.01)
        time.sleep(0.02)
        assert not ta.verify(token)
        assert token.is_expired()

    def test_tampered_token_fails(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "agent-1", {"read"}, {"repo"})
        tampered = DelegationToken(
            token_id=token.token_id, issuer="hacker", subject=token.subject,
            permitted_operations=token.permitted_operations,
            resources=token.resources, issued_at=token.issued_at,
            expires_at=token.expires_at, chain_depth=token.chain_depth,
            signature=token.signature,
        )
        assert not ta.verify(tampered)


class TestPermissions:
    def test_permits_valid_operation(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "a1", {"read", "write"}, {"repo", "bus"})
        assert token.permits("read", "repo")
        assert token.permits("write", "bus")

    def test_denies_unpermitted_operation(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "a1", {"read"}, {"repo"})
        assert not token.permits("delete", "repo")
        assert not token.permits("read", "secrets")

    def test_expired_denies_all(self):
        ta = TokenAuthority()
        token = ta.issue("admin", "a1", {"read"}, {"repo"}, ttl_seconds=0.01)
        time.sleep(0.02)
        assert not token.permits("read", "repo")


class TestDelegation:
    def test_delegate_creates_child(self):
        ta = TokenAuthority()
        parent = ta.issue("admin", "agent-1", {"read"}, {"repo"}, chain_depth=0)
        child = ta.delegate(parent, "agent-2")
        assert child.issuer == "agent-1"
        assert child.subject == "agent-2"
        assert child.chain_depth == 1

    def test_delegate_inherits_permissions(self):
        ta = TokenAuthority()
        parent = ta.issue("admin", "a1", {"read", "write"}, {"repo"})
        child = ta.delegate(parent, "a2")
        assert child.permitted_operations == parent.permitted_operations
        assert child.resources == parent.resources

    def test_max_chain_depth_enforced(self):
        ta = TokenAuthority()
        t0 = ta.issue("admin", "a1", {"read"}, {"repo"}, chain_depth=0)
        t1 = ta.delegate(t0, "a2")
        t2 = ta.delegate(t1, "a3")
        with pytest.raises(ValueError, match="Chain depth"):
            ta.delegate(t2, "a4")

    def test_delegate_from_expired_fails(self):
        ta = TokenAuthority()
        parent = ta.issue("admin", "a1", {"read"}, {"repo"}, ttl_seconds=0.01)
        time.sleep(0.02)
        with pytest.raises(ValueError, match="invalid or expired"):
            ta.delegate(parent, "a2")
