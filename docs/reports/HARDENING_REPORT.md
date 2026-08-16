# Five gaps closed

*Account takeover, drift monitoring, storage engine, refresh tokens, email verification.*

---

## 1. The account takeover (critical)

### What was wrong

`POST /api/v1/auth/forgot-password` answered with the reset token **in the response body**.

```python
return ForgotPasswordResponse(
    message="If that email is registered, a reset code has been issued.",
    reset_token=reset_token,      # ← here
)
```

The comment beside it argued that the message text was identical whether or
not the address matched, so the route could not be used to enumerate
accounts. That was true, and beside the point. Anyone who knew a registered
address could POST it, read the token out of the JSON, and set that
account's password.

Argon2 hashing, the per-email login throttle and JWT signing were all
irrelevant to an attacker who never had to guess anything. `SECURITY.md`
did not mention it.

### What it is now

The token leaves through `services/identity/mail_service.py` and nowhere
else. The response carries only `delivery` — where it went:

| value | meaning |
|---|---|
| `email` | a mail server accepted it |
| `server_log` | no mail server configured; it is in the server log, readable by whoever runs the deployment |
| `none` | delivery failed, **or** the address matched no account |

`none` covering both failure and unknown-address is deliberate: neither
field distinguishes a registered address from an unregistered one, so the
enumeration property the old comment was proud of is still there — now
alongside the property that actually mattered.

Three more things the fix carries:

- **A reset ends existing sessions.** A reset is the answer to "somebody
  else may be in my account"; if their session survives it, the reset was
  cosmetic. Every refresh token is revoked.
- **Provider accounts are still unclaimable.** A GitHub account has no
  password, so no reset token is minted for one — otherwise this route
  could manufacture a credential for an account that deliberately has none.
- **The log fallback is a downgrade, not a loophole.** Server-log access
  already implies control of the deployment, so nothing is lost that was
  not already lost. The code never goes to the caller.

### Pinned by

`tests/api/test_auth_hardening.py::test_the_code_is_nowhere_in_the_response`
reads the code out of the message that was actually sent and asserts it
appears nowhere in the response JSON — not under the old key, not under a
new one.

---

## 2. Refresh tokens

### What was wrong

Access tokens lasted 60 minutes and there was nothing else. Hour two was a
401 in the middle of whatever the user was doing, an instant logout and a
re-typed password — and because the app polls, it usually landed on a
background call rather than a click.

### What it is now

A refresh token with a 30-day life. The interesting half is what stops a
30-day bearer credential being worse than the problem it solves:

- **It is revocable.** Every jti is recorded in
  `services/identity/refresh_token_service.py`. A correctly signed token
  whose jti is not in the store is worthless, which is what makes logout
  mean something.
- **It is single-use.** Every refresh spends the token it was given and
  issues a new one.
- **A replay burns everything.** A jti coming back twice is either a client
  retrying or an attacker replaying a stolen copy, and the request cannot
  tell them apart. Both are logged out; the real user recovers with a
  password the attacker does not have.
- **Every rejection looks the same.** "Already used" and "never existed"
  return the same status and code — telling them apart tells an attacker
  holding a stolen token whether it is worth trying elsewhere.
- **The token itself is never stored.** Only the jti, the user, the expiry
  and a flag. A store holding whole refresh tokens is a file full of live
  credentials.

### A bug found during implementation

The first version pruned spent rows on every write — they cannot be used,
so why keep them. That silently **disabled reuse detection**: refreshing
rotates A into B, the write that stores B prunes the just-spent A, and a
replay of A then finds nothing and is answered `unknown`. Refused, yes, but
silently — no alarm, and the attacker's own token B keeps working.

`test_a_replay_burns_every_session_the_account_has` caught it. Spent rows
are now kept as tombstones until their own expiry: **the tombstone is the
detector.**

### Client side

`frontend/assets/js/core/api.js` retries once on a 401 and funnels every
refresh through a single promise. Five concurrent 401s must renew *once* —
five parallel refreshes would spend the token five times, and the store
treats a token spent twice as stolen. Racing there would log the user out
for being quick.

---

## 3. Email verification

Anybody could register any address. Now registration mints a verification
token that names both the account and the address, and
`POST /auth/verify-email` consumes it.

Design decisions worth stating:

- **Not a login gate.** `email_verified` is reported, never enforced.
  Switching enforcement on would have locked out every existing account and
  every demo the moment it shipped, on deployments that may have no mail
  server. Unverified accounts are told, not blocked.
- **Unauthenticated on purpose.** The token *is* the proof. Requiring a
  bearer token would mean somebody who opens the link on their phone —
  where they are not signed in — cannot verify at all.
- **The address is in the token and re-checked.** Without that, a token
  issued before an address change would verify the *new* one: the user
  would have proved they can read an inbox they have since left.
- **Provider accounts arrive verified.** GitHub already established it;
  asking again would be theatre.

---

## 4. Input-drift monitoring

### What was wrong

Every number on the model-performance page describes a held-out split from
training time. Nothing compared the rows arriving *today* to the rows the
models learned from. A model can be 97% accurate on its own test set and
still answer confidently about people it has no basis for.

### The mistake this nearly shipped with

The obvious implementation is PSI per user. It is wrong, and the first
version did it.

PSI compares two **distributions**. One person's thirty days are far more
concentrated than 93,000 rows from thousands of people — an ordinary user
who sleeps 6.5–7.5 hours lands in two or three reference deciles and scores
past the "significant shift" threshold for that reason alone. A simulated
user drawn from near the training medians came back `significant` on *every
feature*. A gauge that reads red for everybody is broken.

### What it is now

Two questions, two metrics:

| scope | question | metric | why |
|---|---|---|---|
| **per user** | do my days fall where the model has data? | share of days outside the training p5–p95 | a coverage question, not a distribution comparison |
| **deployment** | has the user population moved away from training? | PSI, pooled over every stored check-in | a real distribution comparison, and pooled bucket proportions describe nobody in particular |

Verified against the shipped reference:

| | ordinary user | far-out user |
|---|---|---|
| worst feature | 7% of days in the tails → `covered` | 100% → `extrapolating` |

| | pooled near training | pooled shifted |
|---|---|---|
| worst PSI | 0.249 `moderate` | 8.283 `significant` |

The reference grids were already in `artifacts/cohort_reference.json` — 101
quantile points per feature, shipped for the cohort panel. Taking every
tenth point gives ten buckets each holding exactly 10% of training by
construction, so no reference histogram has to be stored.

`GET /api/v1/model-performance/drift`. Below 8 days there is no result;
below 20 the result comes back `reliable: false`.

---

## 5. SQLite storage with migrations

### What was wrong

Every write rewrote a whole JSON file, and every read-modify-write queued
behind one OS advisory lock. The cost of saving one journal page grew with
the size of *every* account's journal, and two workers was not a supported
deployment.

### What it is now

`services/storage/sqlite_storage.py` — the same `StorageBackend` interface,
with a real transaction underneath.

- `BEGIN IMMEDIATE` takes the write lock up front. Deferred would let two
  transactions both read, both decide, and one fail to upgrade — the
  lost-update race the file lock existed to prevent, reintroduced.
- WAL, so readers never block the writer.
- `records(id, store, data, user_id, written_at_utc)` where `user_id` is a
  **generated column** over `json_extract(data, '$.user_id')` — not a
  second copy that can drift, and indexed with `store`, so a per-user
  lookup is a search rather than a scan of every account's rows.
- The payload stays JSON rather than becoming typed columns: fifty-nine
  services each write whatever keys they like, and imposing a schema on top
  would mean rewriting all of them before a single row could move.

### Migrations

`services/storage/migrations.py` — numbered steps, applied once, in order,
each in its own transaction, recorded in `schema_migrations`. Forward only:
a down-migration that drops a column drops the data in it, and "restore the
backup" is the honest answer to a bad deploy.

A step that fails leaves the database at the last version that completed,
not in a state that is neither.

### Not the default

JSON stays default. Switching it silently would strand every existing
install behind an empty database.

```bash
python3 -m services.storage.import_json           # dry run — prints the plan
python3 -m services.storage.import_json --write   # copies; deletes nothing
DWAI_STORAGE_BACKEND=sqlite python run.py
```

The JSON files are left in place, so unsetting the variable reverts.

### Verified how

Not by asserting the three interface methods exist — the services do
upsert-by-key, cross-user deletes and read-modify-write inside
transactions. So **the entire API test suite was run against SQLite**:

```
DWAI_STORAGE_BACKEND=sqlite DWAI_SQLITE_PATH=/tmp/dwai.db \
  python3 -m unittest tests.test_api tests.test_auth_hardening tests.test_demo_session
→ 96 tests, OK
```

and the resulting database held real data:

| store | rows |
|---|---|
| plan_progress.json | 423 |
| prediction_history.json | 176 |
| league.json | 99 |
| refresh_tokens.json | 80 |
| journal.json | 48 |
| plan_locks.json | 23 |
| accounts.json | 12 |
| personal.json | 8 |

Plus ten threads racing to append inside transactions, finishing with ten
rows rather than fewer.

---

## What is still not done

- **No CI.** `.github/workflows/` is still empty. The suite passes; nothing
  runs it automatically.
- **No screenshots.** Deliberate — you said you would record the video.
- **Verification is not enforced.** By design, see §3. A deployment with a
  real mail server can be made stricter; nothing currently does.
- **The population PSI is visible to any signed-in user.** It is aggregate
  and reveals nobody, but there is no operator role, and if one is ever
  added this belongs behind it.
- **Volatile users are still under-covered by the band model** (0.863
  against a 0.90 target). Unchanged by this work; recorded in
  `docs/reports/BAND_MODEL_REPORT.md`.

---

## Files

| File | What |
|---|---|
| `services/identity/mail_service.py` | SMTP / log / memory transports; never raises, never returns a secret |
| `services/identity/refresh_token_service.py` | jti store, rotation, reuse detection, tombstones |
| `services/ml/drift_service.py` | per-user coverage + pooled PSI |
| `services/storage/sqlite_storage.py` | the backend |
| `services/storage/migrations.py` | versioned schema |
| `services/storage/import_json.py` | the one-command move |
| `tests/api/test_auth_hardening.py` | 38 tests |
| `tests/ml/test_drift_monitoring.py` | 28 tests |
| `tests/storage/test_sqlite_storage.py` | 39 tests |
