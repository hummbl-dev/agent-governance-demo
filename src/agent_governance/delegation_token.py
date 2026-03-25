"""HMAC-SHA256 signed delegation tokens for agent capability binding."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class DelegationToken:
    token_id: str
    issuer: str
    subject: str
    permitted_operations: FrozenSet[str]
    resources: FrozenSet[str]
    issued_at: float
    expires_at: float
    chain_depth: int
    signature: str

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def permits(self, operation: str, resource: str) -> bool:
        if self.is_expired():
            return False
        return operation in self.permitted_operations and resource in self.resources

    def remaining_seconds(self) -> float:
        return max(0.0, self.expires_at - time.time())


class TokenAuthority:
    MAX_CHAIN_DEPTH = 3

    def __init__(self, secret: str = "token-secret"):
        self._secret = secret.encode()

    def issue(
        self,
        issuer: str,
        subject: str,
        operations: set[str],
        resources: set[str],
        ttl_seconds: float = 300.0,
        chain_depth: int = 0,
    ) -> DelegationToken:
        if chain_depth >= self.MAX_CHAIN_DEPTH:
            raise ValueError(
                f"Chain depth {chain_depth} exceeds maximum ({self.MAX_CHAIN_DEPTH})"
            )
        now = time.time()
        token_id = str(uuid.uuid4())
        payload = self._payload(
            token_id, issuer, subject, frozenset(operations),
            frozenset(resources), now, now + ttl_seconds, chain_depth
        )
        signature = self._sign(payload)
        return DelegationToken(
            token_id=token_id, issuer=issuer, subject=subject,
            permitted_operations=frozenset(operations),
            resources=frozenset(resources),
            issued_at=now, expires_at=now + ttl_seconds,
            chain_depth=chain_depth, signature=signature,
        )

    def verify(self, token: DelegationToken) -> bool:
        payload = self._payload(
            token.token_id, token.issuer, token.subject,
            token.permitted_operations, token.resources,
            token.issued_at, token.expires_at, token.chain_depth
        )
        expected = self._sign(payload)
        return hmac.compare_digest(token.signature, expected) and not token.is_expired()

    def delegate(self, parent: DelegationToken, new_subject: str) -> DelegationToken:
        if not self.verify(parent):
            raise ValueError("Cannot delegate from invalid or expired token")
        return self.issue(
            issuer=parent.subject, subject=new_subject,
            operations=set(parent.permitted_operations),
            resources=set(parent.resources),
            ttl_seconds=parent.remaining_seconds(),
            chain_depth=parent.chain_depth + 1,
        )

    def _payload(
        self, token_id: str, issuer: str, subject: str,
        ops: FrozenSet[str], resources: FrozenSet[str],
        issued_at: float, expires_at: float, chain_depth: int,
    ) -> bytes:
        return json.dumps({
            "id": token_id, "iss": issuer, "sub": subject,
            "ops": sorted(ops), "res": sorted(resources),
            "iat": issued_at, "exp": expires_at, "depth": chain_depth,
        }, sort_keys=True).encode()

    def _sign(self, payload: bytes) -> str:
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
