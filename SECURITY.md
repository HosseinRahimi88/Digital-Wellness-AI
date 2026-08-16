# Security note — user data in git history

## What happened

`storage/` is where the running app writes its data:

- `storage/accounts.json` — one record per account: email address,
  display name, argon2id password hash, and profile preferences.
- `storage/prediction_history.json` — every day a user has logged.

Both files were **tracked by git**. Anyone who ran the app in a
checkout and then committed would commit whatever was in them, and that
is what happened: real accounts were captured in early commits and
pushed to the default branch of a **public** repository.

Three accounts are affected. Each entry exposes an email address, a
display name, and an argon2id password hash.

## What is and is not at risk

**Exposed:** the email addresses and display names. Those are readable
by anyone, and they cannot be un-read.

**Not directly exposed:** the passwords themselves. They are argon2id
hashes (`m=65536, t=3, p=4` — the OWASP-recommended parameters), which
is a deliberately slow, memory-hard function with a per-record salt.
There is no way to reverse one, and brute-forcing a strong password
against these parameters is not practical.

That is a reason not to panic, **not** a reason to leave it. A weak or
reused password is still worth attacking offline at leisure, and the
attacker gets unlimited attempts once they hold the hash.

## Do this

1. **Tell the three people.** They should change that password anywhere
   else they used it. This is the step that actually matters, and it
   does not depend on any of the ones below.
2. **Decide about the history.** The commits are already public and
   likely cloned or cached. Removing them is still worth doing, but
   treat it as reducing further exposure, not as undoing it:
   - Rewrite with `git filter-repo` (preferred) or BFG:
     ```
     git filter-repo --path storage/accounts.json \
                     --path storage/prediction_history.json --invert-paths
     ```
   - Force-push the rewritten branches, and ask anyone with a clone to
     re-clone. Old commits can linger on GitHub until it prunes them;
     support can be asked to expire cached views.
3. **Consider making the repository private** until the above is done,
   which stops new copies immediately and costs nothing.

## What has been changed already

- `storage/` contents are gitignored, and both data files are untracked
  (`git rm --cached`). `storage/.gitkeep` keeps the directory visible in
  a fresh checkout; nothing else in there is ever committed again.
- `*.lock` and `*.tmp` — the transaction sidecars written next to the
  data — are ignored too.
- `tests/storage/test_no_user_data_committed.py` fails the build if a storage
  data file becomes tracked again, and asks git directly rather than
  trusting that a line in `.gitignore` has the intended effect.
- The app was verified to start from an **empty** `storage/`: register,
  log in and authenticate all succeed, and the files are created on
  first write. Untracking them does not break a fresh install.

## For anyone deploying this

The JSON file storage is a demo-grade backend. It has no encryption at
rest and no access control beyond filesystem permissions. If this ever
holds real users' data, put it behind a real database with encrypted
storage and backups, and keep it off any machine whose filesystem gets
committed, synced, or shared.
