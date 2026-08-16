"""
Tests: JavaScript call-arity safety.

Why this exists
----------------
JavaScript never complains when a function is called with too few
arguments - the missing parameters are simply `undefined`. That produced a
real, user-facing bug in this project: the AI menu called

    chatCompletion(apiKey, envelope.messages)          # 2 args

against

    chatCompletion(apiKey, systemPrompt, messages)     # 3 params

so `messages` was undefined, and `buildRequest` then ran
`messages.filter(...)`. Every one of the 55 menu items threw a TypeError
the moment the external connector was enabled, and the catch block
reported it as a provider error - sending debugging in the wrong
direction entirely.

What this checks
-----------------
Every call through a `window.DW*` namespace is compared against the
target function's declared parameter list. A missing trailing argument is
only reported when it can actually throw, which needs two refinements
that a naive check gets wrong:

  1. Idiomatic optional parameters. `function explain(topicKey, opts)`
     with `opts = opts || {}` in the body is safe and extremely common
     here (29 such call sites). Only unguarded uses count.

  2. Parameters that are merely forwarded. The bug above is invisible if
     you inspect `chatCompletion`'s body alone, because it never touches
     `messages` - it just passes it to `buildRequest`. So a parameter is
     followed through local calls (up to MAX_DEPTH hops) into the
     corresponding parameter of the callee.

Both refinements were validated against the pre-fix source: without (2)
the check passed vacuously on the exact bug it was written to catch.

Run standalone:
    python3 -m tests.test_js_call_arity
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JS_DIR = PROJECT_ROOT / "frontend" / "assets" / "js"
MAX_DEPTH = 4


def strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?<!:)//[^\n]*", "", src)


def split_args(text: str) -> int:
    """Count top-level comma-separated arguments in a call's parentheses."""
    if not text.strip():
        return 0
    depth = 0
    count = 1
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            count += 1
        i += 1
    return count


def read_call_args(src: str, open_paren: int) -> str | None:
    """Return the raw text inside the call parentheses starting at open_paren."""
    depth = 0
    quote = None
    i = open_paren
    while i < len(src):
        c = src[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return src[open_paren + 1 : i]
        i += 1
    return None



def collect_definitions() -> dict[str, dict]:
    """Map exported name -> {params, required, file, owner}."""
    defs: dict[str, dict] = {}
    # function declarations, including async
    fn_re = re.compile(r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)")
    # arrow / function expressions assigned to a const
    arrow_re = re.compile(
        r"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\s*)?\(([^)]*)\)\s*=>"
    )
    export_re = re.compile(r"window\.(DW[\w$]*)\s*=\s*\{(.*?)\};", re.S)

    per_file: dict[str, dict[str, str]] = {}
    for path in sorted(JS_DIR.glob("*.js")):
        src = strip_comments(path.read_text(encoding="utf-8"))
        local: dict[str, str] = {}
        for m in list(fn_re.finditer(src)) + list(arrow_re.finditer(src)):
            local[m.group(1)] = m.group(2)
        per_file[path.name] = local

        for em in export_re.finditer(src):
            owner = em.group(1)
            body = em.group(2)
            for entry in body.split(","):
                entry = entry.strip()
                if not entry:
                    continue
                if ":" in entry:
                    exported, target = (x.strip() for x in entry.split(":", 1))
                else:
                    exported = target = entry
                if target in local:
                    params = [p.strip() for p in local[target].split(",") if p.strip()]
                    required = [
                        p for p in params
                        if "=" not in p and not p.startswith("...")
                    ]
                    defs[f"{owner}.{exported}"] = {
                        "params": params,
                        "required": len(required),
                        "declared": len(params),
                        "file": path.name,
                        "variadic": any(p.startswith("...") for p in params),
                    }
    return defs



def local_functions(src: str) -> dict[str, tuple[list[str], str]]:
    """name -> (params, body) for every function declared in this file."""
    out: dict[str, tuple[list[str], str]] = {}
    pat = re.compile(
        r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{"
        r"|\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\s*)?\(([^)]*)\)\s*=>\s*\{"
    )
    for m in pat.finditer(src):
        name = m.group(1) or m.group(3)
        params_raw = m.group(2) if m.group(1) else m.group(4)
        params = [p.strip() for p in (params_raw or "").split(",") if p.strip()]
        i = m.end() - 1
        depth = 0
        quote = None
        while i < len(src):
            c = src[i]
            if quote:
                if c == "\\":
                    i += 2
                    continue
                if c == quote:
                    quote = None
            elif c in "\"'`":
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out[name] = (params, src[m.end():i])
                    break
            i += 1
    return out



GUARD_FORMS = [
    r"(?<![\w$.]){p}\s*\|\|", r"(?<![\w$.]){p}\s*&&", r"!\s*{p}(?![\w$])",
    r"(?<![\w$.]){p}\s*\?", r"(?<![\w$.]){p}\s*=[^=]", r"typeof\s+{p}",
    r"Array\.isArray\(\s*{p}\s*\)", r"(?<![\w$.]){p}\s*[=!]=\s*null",
    r"(?<![\w$.]){p}\s*\?\?",
]


def classify(fns: dict, body: str, param: str, depth: int = 0, seen=None) -> tuple[str, str]:
    """Return (verdict, trail)."""
    seen = seen or set()
    p = re.escape(param)
    if not re.search(rf"(?<![\w$.]){p}(?![\w$])", body):
        return "UNUSED", ""
    if any(re.search(g.format(p=p), body) for g in GUARD_FORMS):
        return "GUARDED", ""
    # direct dereference or spread
    if re.search(rf"(?<![\w$.]){p}\s*[.\[(]", body) or re.search(rf"\.\.\.\s*{p}(?![\w$])", body):
        return "UNGUARDED", f"{param} used directly"
    # forwarded into a local function -> follow it
    if depth < MAX_DEPTH:
        for m in re.finditer(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(", body):
            callee = m.group(1)
            if callee not in fns or callee in seen:
                continue
            args_text = read_call_args(body, m.end() - 1)
            if args_text is None:
                continue
            args = _split_top(args_text)
            for idx, a in enumerate(args):
                if re.fullmatch(rf"\s*{p}\s*", a):
                    callee_params, callee_body = fns[callee]
                    if idx < len(callee_params):
                        target = callee_params[idx]
                        verdict, trail = classify(
                            fns, callee_body, target, depth + 1, seen | {callee}
                        )
                        if verdict == "UNGUARDED":
                            return "UNGUARDED", f"{param} -> {callee}({target}); {trail}"
    return "GUARDED", ""


def _split_top(text: str) -> list[str]:
    parts, depth, quote, cur = [], 0, None, ""
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            cur += c
            if c == "\\":
                cur += text[i + 1: i + 2]; i += 2; continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote = c; cur += c
        elif c in "([{":
            depth += 1; cur += c
        elif c in ")]}":
            depth -= 1; cur += c
        elif c == "," and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += c
        i += 1
    if cur.strip() or parts:
        parts.append(cur)
    return parts




def find_real_risks(js_dir: Path = JS_DIR) -> list[str]:
    """Call sites where a missing argument reaches an unguarded use."""
    global JS_DIR
    previous = JS_DIR
    JS_DIR = js_dir
    try:
        defs = collect_definitions()
        per_file_fns, per_file_src = {}, {}
        for path in sorted(js_dir.glob("*.js")):
            src = strip_comments(path.read_text(encoding="utf-8"))
            per_file_src[path.name] = src
            per_file_fns[path.name] = local_functions(src)

        risks: list[str] = []
        for path in sorted(js_dir.glob("*.js")):
            src = per_file_src[path.name]
            for key, info in defs.items():
                owner, fname = key.split(".", 1)
                for m in re.finditer(rf"window\.{re.escape(owner)}\.{re.escape(fname)}\s*\(", src):
                    args_text = read_call_args(src, m.end() - 1)
                    if args_text is None:
                        continue
                    n = split_args(args_text)
                    if n >= info["required"]:
                        continue
                    fns = per_file_fns[info["file"]]
                    if fname not in fns:
                        continue
                    body_text = fns[fname][1]
                    line = src[: m.start()].count("\n") + 1
                    for param in info["params"][n:]:
                        verdict, trail = classify(fns, body_text, param)
                        if verdict == "UNGUARDED":
                            risks.append(
                                f"{path.name}:{line} {key} called with {n} arg(s); "
                                f"missing '{param}' reaches an unguarded use ({trail})"
                            )
        return risks
    finally:
        JS_DIR = previous


class TestCallArity(unittest.TestCase):

    def test_parser_found_the_exported_surface(self):
        """Guard against the parser silently matching nothing, which would
        make every other assertion here pass vacuously."""
        defs = collect_definitions()
        self.assertGreater(
            len(defs), 50,
            "Expected many window.DW* exports; the parser or file layout changed",
        )

    def test_no_call_passes_too_few_arguments_to_an_unguarded_parameter(self):
        risks = find_real_risks()
        self.assertEqual(
            risks, [],
            "A call omits an argument that the callee uses without a guard, "
            "which throws at runtime:\n  " + "\n  ".join(risks),
        )


def _main() -> None:
    risks = find_real_risks()
    print(f"scanned {len(collect_definitions())} exported DW* functions")
    print("REAL RISK: " + (f"{len(risks)}" if risks else "none"))
    for r in risks:
        print("  " + r)


if __name__ == "__main__":
    _main()
