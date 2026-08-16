"""The server-side half of a refresh token.

WHY A STORE AT ALL
------------------
An access token is safe to be un-revocable because it dies in an hour.
A refresh token lives for thirty days, and a thirty-day bearer secret
that cannot be withdrawn is not a session - it is a permanent key. So
every refresh token's `jti` is recorded here, and a signed token whose
jti is not in this store is worthless. Logging out, or having a token
stolen, actually ends the session.

ROTATION, AND WHAT A REPLAY MEANS
---------------------------------
Every successful refresh consumes the token it was given and issues a
new one. That makes a refresh token single-use, which turns theft into
something detectable: if a jti that has already been consumed comes back,
either the legitimate client is retrying or an attacker is replaying a
copy - and there is no way to tell which from the request alone.

The response to that ambiguity is the standard one, and it is
deliberately harsh: **every** refresh token for that user is revoked, so
both the attacker and the victim are logged out and the victim has to
sign in with a password the attacker does not have. Being logged out is
an annoyance; a silently shared session is not.

WHAT IS STORED
--------------
Only the jti, the user, the expiry and a flag. Never the token itself:
a store that held whole refresh tokens would be a file full of live
credentials, which is exactly the thing being defended against.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from core import paths
from services.storage.base import StorageBackend
from services.storage.sqlite_storage import backend_for

logger = logging.getLogger(__name__)

DEFAULT_REFRESH_TOKEN_PATH = paths.storage_file("refresh_tokens.json")

# Above this many live tokens for one user, the oldest are dropped on
# the next issue. A person has a handful of devices; an unbounded list
# is just somewhere for abandoned sessions to pile up forever.
MAX_LIVE_TOKENS_PER_USER = 10

# Spent tokens are kept as tombstones so a replay is DETECTED rather
# than merely refused - see _pruned. They are not sessions, so they get
# their own budget; without one the file would grow by a row per refresh
# forever.
MAX_TOMBSTONES_PER_USER = 50


@dataclass(slots=True)
class RefreshRecord:
    user_id: str
    jti: str
    expires_at_utc: str
    created_at_utc: str
    revoked: bool = False
    # Why it stopped being usable, for anyone reading the store later.
    revoked_reason: str = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(stamp: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class RefreshTokenService:
    """One user's refresh tokens."""

    def __init__(self, user_id: str, backend: Optional[StorageBackend] = None) -> None:
        self.user_id = user_id
        self._backend = backend or backend_for(DEFAULT_REFRESH_TOKEN_PATH)

    # ----------------------------------------------------------- reading
    def _mine(self, records: list[dict]) -> list[dict]:
        return [r for r in records if r.get("user_id") == self.user_id]

    def live_count(self) -> int:
        now = _now()
        return sum(
            1 for r in self._mine(self._backend.read_all())
            if not r.get("revoked") and (_parse(r.get("expires_at_utc") or "") or now) > now
        )

    # ----------------------------------------------------------- writing
    def issue(self, jti: str, expires_at: datetime) -> None:
        """Record a newly minted token as live."""
        with self._backend.transaction() as records:
            rows = list(records)
            rows.append({
                "user_id": self.user_id,
                "jti": jti,
                "expires_at_utc": expires_at.isoformat(),
                "created_at_utc": _now().isoformat(),
                "revoked": False,
                "revoked_reason": "",
            })
            self._backend.commit(self._pruned(rows))

    def consume(self, jti: str) -> tuple[bool, str]:
        """Spend a refresh token exactly once.

        Returns (accepted, reason). A False comes with one of:

          "unknown"  - correctly signed, but this server never issued it
                       or has already pruned it. Treated as replay.
          "reused"   - issued by this server and already spent. THIS is
                       the dangerous one, and it revokes everything the
                       user has (see the module docstring).
          "revoked"  - explicitly withdrawn, e.g. by a logout.
          "expired"  - past its own expiry.

        The revoke-everything response happens inside the same
        transaction that detected the reuse, so a second replay arriving
        concurrently cannot slip through the gap between detecting and
        reacting.
        """
        with self._backend.transaction() as records:
            rows = list(records)
            target = None
            for row in rows:
                if row.get("user_id") == self.user_id and row.get("jti") == jti:
                    target = row
                    break

            if target is None:
                self._backend.commit(rows)
                return (False, "unknown")

            expires_at = _parse(target.get("expires_at_utc") or "")
            if target.get("revoked"):
                reason = target.get("revoked_reason") or ""
                if reason == "rotated":
                    # Already spent by a successful refresh. Someone has
                    # a copy of a token that should no longer exist.
                    logger.warning(
                        "Refresh token reuse detected for user %s - revoking every live "
                        "token for this account.", self.user_id,
                    )
                    for row in rows:
                        if row.get("user_id") == self.user_id and not row.get("revoked"):
                            row["revoked"] = True
                            row["revoked_reason"] = "reuse_detected"
                    self._backend.commit(rows)
                    return (False, "reused")
                self._backend.commit(rows)
                return (False, "revoked")

            if expires_at is not None and expires_at <= _now():
                target["revoked"] = True
                target["revoked_reason"] = "expired"
                self._backend.commit(rows)
                return (False, "expired")

            target["revoked"] = True
            target["revoked_reason"] = "rotated"
            self._backend.commit(rows)
            return (True, "ok")

    def revoke_all(self, reason: str = "logout") -> int:
        """End every session this user has. Returns how many were live."""
        ended = 0
        with self._backend.transaction() as records:
            rows = list(records)
            for row in rows:
                if row.get("user_id") == self.user_id and not row.get("revoked"):
                    row["revoked"] = True
                    row["revoked_reason"] = reason
                    ended += 1
            self._backend.commit(rows)
        return ended

    def delete_users(self, user_ids: list[str]) -> None:
        """Drop every record for these users - privacy delete, demo teardown.

        Takes a list and does one pass, for the same reason
        HistoryService.delete_users does: a demo with ten bot friends
        would otherwise rewrite the whole file eleven times.
        """
        wanted = set(user_ids or ())
        if not wanted:
            return
        with self._backend.transaction() as records:
            self._backend.commit([
                r for r in records if r.get("user_id") not in wanted
            ])

    # ---------------------------------------------------------- internals
    def _pruned(self, rows: list[dict]) -> list[dict]:
        """Drop this user's EXPIRED rows and cap the live ones.

        A revoked row is deliberately kept until its own expiry, and this
        is the whole reason rotation is worth anything.

        The obvious version of this method also dropped spent rows - they
        cannot be used, so why keep them - and that quietly disabled
        reuse detection: refreshing rotates token A into token B, the
        write that stores B prunes the just-spent A, and a replay of A
        then finds nothing and is answered "unknown". Refused, yes, but
        silently: the stolen copy looks exactly like a typo, no alarm is
        raised, and the attacker's own token B keeps working. The tombstone
        IS the detector, so it lives as long as the token it replaced
        would have.

        Only ever touches this user's records - another account's rows
        pass through untouched, because this runs inside a transaction
        over the whole shared file, and a busy account must not evict
        anybody else's sessions.
        """
        now = _now()
        keep: list[dict] = []
        mine_live: list[dict] = []
        mine_spent: list[dict] = []
        for row in rows:
            if row.get("user_id") != self.user_id:
                keep.append(row)
                continue
            expires_at = _parse(row.get("expires_at_utc") or "")
            if expires_at is not None and expires_at <= now:
                # Past its own expiry. decode_refresh_token() would
                # refuse it before the store was ever consulted, so the
                # tombstone has nothing left to detect.
                continue
            (mine_spent if row.get("revoked") else mine_live).append(row)

        # The cap is on LIVE tokens - the number of devices somebody is
        # signed in on. Tombstones are not sessions and are not counted,
        # or a handful of refreshes would push every real session out.
        mine_live.sort(key=lambda r: r.get("created_at_utc") or "")
        if len(mine_live) > MAX_LIVE_TOKENS_PER_USER:
            evicted = mine_live[:-MAX_LIVE_TOKENS_PER_USER]
            for row in evicted:
                row["revoked"] = True
                row["revoked_reason"] = "evicted"
            mine_spent.extend(evicted)
            mine_live = mine_live[-MAX_LIVE_TOKENS_PER_USER:]

        # Tombstones are bounded too. Without this the file grows by one
        # row per refresh forever, and the oldest ones are the least
        # useful: a replay of a token spent weeks ago is far less likely
        # than one spent minutes ago.
        mine_spent.sort(key=lambda r: r.get("created_at_utc") or "")
        if len(mine_spent) > MAX_TOMBSTONES_PER_USER:
            mine_spent = mine_spent[-MAX_TOMBSTONES_PER_USER:]

        return keep + mine_spent + mine_live
