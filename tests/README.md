# Tests

1,716 of them, grouped to mirror `services/`. A file's folder tells you
what it is about, and running one folder is a useful thing to do while
working on that area.

```bash
python3 -m unittest discover -s tests -t .            # everything
python3 -m unittest discover -s tests/wellness -t .   # one area
python3 -m unittest tests.api.test_auth_hardening -v  # one file
```

The `-t .` is not optional. It sets the top-level directory, and without
it the imports in every test resolve against `tests/` rather than the
project root.

| Folder | What is in it |
|---|---|
| `api/` | HTTP surface: routers, schemas, auth flows, the demo endpoint |
| `ml/` | The trained models and everything derived from a prediction |
| `wellness/` | The weekly plan, its band, its violations, recommendations |
| `identity/` | Accounts, tokens, history, the journal, CSV and reports |
| `social/` | Friends League, chat, badges and gamification |
| `insight/` | Analytics, trends, simulations, the reflection layer |
| `coach/` | The rule-based Digital Coach and the optional AI connector |
| `storage/` | Both backends, locking, corruption, the no-user-data rule |
| `frontend/` | Pages and JS modules, checked against their real files |
| `js/` | Node runners: coach coverage, precision, refusals |

## Two rules that are load bearing

**Never compute the project root from a file's own depth.** Import it:

```python
from core import paths
REPO_ROOT = paths.PROJECT_ROOT
```

Fifty-two files used to write `Path(__file__).resolve().parents[1]`.
Grouping this tree would have moved every one of them a level deeper, and
they would not have raised - they would have pointed at `tests/`, found
no frontend and no artifacts, and gone green by asserting over empty
lists. The same shape of bug the `services/` move produced.

`tests/_test_support.py` is the single exception, and says so in place:
it is the module that puts the project root *on* `sys.path`, so importing
`core` to locate `core` would be circular.

**Import the support module first.** `import tests._test_support` installs
the offline `pwdlib`/`shap` stubs, routes outbound mail to memory, and
does the `sys.path` bootstrap. Anything imported before it may resolve
against the wrong thing or reach the network.
