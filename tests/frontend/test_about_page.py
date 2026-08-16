"""The About page: the map, the team, and the book.

Three sections were added here at once, and each has a way of going
wrong that nobody notices in the browser they happen to be using:

  * the MAP makes a factual claim at every station. A number that
    drifts from the code is worse than no number at all, so the figures
    a reader can check against a file are checked here against that
    file - the field count, the count in its own headline, and the fact
    that two stations are about what the project decided it could NOT
    claim.
  * the TEAM is four real people's own words, laid out as a résumé in
    five panels. The failure to guard against is a profile that quietly
    grows a contribution nobody claimed, so every panel is pinned:
    each person's own text in four languages, and the R&D role checked
    phrase by phrase against what was actually supplied.
  * the BOOK has limits that live in TWO places - services/
    journal_service.py and the browser. A client that allows a longer
    page than the server does turns a save into a 400 the user cannot
    predict, and a client mood the server rejects does the same. Both
    are compared against the real server constants here.

The node runner loads the actual frontend modules; nothing in this file
reimplements them.

Run: python3 -m unittest tests.frontend.test_about_page -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import tests._test_support  # noqa: F401

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

from core.feature_schema import FEATURE_SCHEMA
from services.identity.journal_service import MAX_TEXT_LENGTH, MOODS

ROOT = paths.PROJECT_ROOT
RUNNER = ROOT / "tests" / "js" / "about_runner.js"
ABOUT_HTML = (ROOT / "frontend" / "about.html").read_text(encoding="utf-8")
# The book and the personal dossier moved off About and onto their own
# page. They are the two parts that are about the READER rather than
# about the project, and they were sitting below the team.
YOU_HTML = (ROOT / "frontend" / "you.html").read_text(encoding="utf-8")
ABOUT_CSS = (ROOT / "frontend" / "assets" / "css" / "about.css").read_text(encoding="utf-8")
LANGS = ("en", "fa", "ar", "zh")

# Persian and Arabic render numerals in their own digits. A test that
# looked for "53" in the Persian string would be asking the page to be
# wrong.
_DIGITS = {
    "fa": "۰۱۲۳۴۵۶۷۸۹",
    "ar": "٠١٢٣٤٥٦٧٨٩",
}


def _localised_digits(number: str, lang: str) -> str:
    table = _DIGITS.get(lang)
    if not table:
        return number
    return "".join(table[int(ch)] if ch.isdigit() else ch for ch in number)


class AboutContent(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        proc = subprocess.run(
            [node, str(RUNNER)], capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            raise AssertionError(f"runner failed:\n{proc.stderr}")
        cls.out = json.loads(proc.stdout)

    # ------------------------------------------------------------- map

    def test_the_map_runs_through_its_four_phases_in_order(self) -> None:
        stations = self.out["stations"]
        self.assertGreaterEqual(len(stations), 12)
        phases = [s["phase"] for s in stations]
        self.assertEqual(set(phases), {"input", "model", "meaning", "action"})
        # The map is read top to bottom, so each phase has to be one
        # unbroken run in this order - a phase that reappears further
        # down reads as a mistake, whatever the station count is.
        order, seen = [], set()
        for phase in phases:
            if not order or order[-1] != phase:
                self.assertNotIn(
                    phase, seen, f"{phase} reappears after another phase: {phases}",
                )
                order.append(phase)
                seen.add(phase)
        self.assertEqual(order, ["input", "model", "meaning", "action"])

    def test_the_headline_count_matches_the_stations(self) -> None:
        """The lede says how many stops there are. It has been wrong
        once already - the stations grew and the sentence did not."""
        words = {12: ("twelve", "دوازده", "اثنتا عشرة", "十二"),
                 13: ("thirteen", "سیزده", "ثلاث عشرة", "十三"),
                 14: ("fourteen", "چهارده", "أربع عشرة", "十四"),
                 15: ("fifteen", "پانزده", "خمس عشرة", "十五")}
        count = len(self.out["stations"])
        self.assertIn(count, words, "add this station count to the table above")
        for lang, word in zip(LANGS, words[count]):
            self.assertIn(
                word, self.out["head"]["lede"][lang].lower(),
                f"the {lang} lede does not say there are {count} stops",
            )

    def test_every_station_speaks_all_four_languages(self) -> None:
        for i, station in enumerate(self.out["stations"], start=1):
            for field in ("title", "body", "proof_label"):
                bundle = station[field] or {}
                missing = [l for l in LANGS if not (bundle.get(l) or "").strip()]
                self.assertFalse(
                    missing, f"station {i} is missing {field} in {missing}",
                )

    def test_the_field_count_on_the_map_is_the_real_one(self) -> None:
        """The map says "a day, in N answers". N is a real number in
        core/feature_schema.py, and it has changed before."""
        claim = next(
            s for s in self.out["stations"]
            if "53" in str(s["proof_value"]) or "feature_schema" in str(s["proof_label"]["en"])
        )
        self.assertEqual(
            int(claim["proof_value"]), len(FEATURE_SCHEMA),
            "the map's field count no longer matches core/feature_schema.py",
        )
        for lang in LANGS:
            # Persian and Arabic write their own digits, so the literal
            # "53" is only expected in the two languages that use it.
            wanted = _localised_digits(str(len(FEATURE_SCHEMA)), lang)
            self.assertIn(
                wanted, claim["title"][lang],
                f"the {lang} title does not carry the field count ({wanted})",
            )

    def test_the_map_still_says_what_was_refused(self) -> None:
        """Two of the stations exist to say what this project
        could NOT claim - the unshipped seven-day regressor, and that
        the training data is synthetic. A map that quietly loses them is
        a marketing page.
        """
        english = " ".join(
            (s["title"]["en"] + " " + s["body"]["en"] + " " + str(s["proof_value"]))
            for s in self.out["stations"]
        ).lower()
        self.assertIn("beats_baseline: false", english)
        self.assertIn("synthetic", english)
        self.assertIn("not shipped", english)

    def test_no_station_claims_a_medical_finding(self) -> None:
        banned = ("diagnos", "cure", "treat your", "clinically proven", "medical advice")
        for i, station in enumerate(self.out["stations"], start=1):
            text = station["body"]["en"].lower()
            for word in banned:
                self.assertNotIn(word, text, f"station {i} claims '{word}'")

    def test_every_station_icon_is_drawn(self) -> None:
        """An icon key with no path renders an empty circle, which reads
        as a missing asset rather than a design choice."""
        source = (ROOT / "frontend" / "assets" / "js" / "about/about-roadmap.js").read_text(encoding="utf-8")
        drawn = set(re.findall(r"^\s{4}(\w+): '<", source, flags=re.M))
        for station in self.out["stations"]:
            self.assertIn(station["icon"], drawn, f"no icon drawn for {station['icon']}")

    # ------------------------------------------------------------ team

    def test_four_people_each_with_their_own_words(self) -> None:
        members = self.out["members"]
        self.assertEqual(len(members), 4)
        self.assertEqual(
            len({m["id"] for m in members}), 4, "two members share an id",
        )
        self.assertEqual(
            len({m["accent"] for m in members}), 4,
            "two members share an accent colour - the cards stop being telling apart",
        )
        for member in members:
            for field in ("name", "role", "tagline", "summary"):
                missing = [l for l in LANGS if not (member[field].get(l) or "").strip()]
                self.assertFalse(missing, f"{member['id']} missing {field} in {missing}")

    def test_every_project_role_is_one_its_owner_stated(self) -> None:
        """All four people described a role on this project, so all four
        carry that panel - and each panel says what its owner said.

        The check that matters is the last one: the R&D role is the one
        most easily inflated into something nobody claimed, so the words
        it must contain are pinned here against what was actually
        supplied - research and development, the idea, technical
        strategy, debugging, and running the team's process.
        """
        by_id = {m["id"]: m for m in self.out["members"]}
        self.assertEqual(set(by_id), {"parisa", "hossein", "parsa", "amirhesam"})
        for member_id, member in by_id.items():
            self.assertTrue(
                member["project"], f"{member_id} has no stated role on this project",
            )
        english = " ".join(i["en"].lower() for i in by_id["amirhesam"]["project"])
        for phrase in ("research and development", "ideator", "technical strategy",
                       "debugging", "team process"):
            self.assertIn(phrase, english, f"the R&D role no longer mentions {phrase!r}")

    def test_every_panel_heading_exists_in_four_languages(self) -> None:
        for key, bundle in self.out["panels"].items():
            missing = [l for l in LANGS if not (bundle.get(l) or "").strip()]
            self.assertFalse(missing, f"panel heading {key} missing {missing}")

    def test_personal_details_are_labelled_in_four_languages(self) -> None:
        for member in self.out["members"]:
            for row in member["personal"]:
                for part in ("label", "value"):
                    missing = [l for l in LANGS if not (row[part].get(l) or "").strip()]
                    self.assertFalse(
                        missing, f"{member['id']} personal {part} missing {missing}",
                    )

    def test_every_profile_bullet_is_translated(self) -> None:
        for member in self.out["members"]:
            for item in member["project"] + member["achievements"]:
                missing = [l for l in LANGS if not (item.get(l) or "").strip()]
                self.assertFalse(
                    missing, f"{member['id']} has a bullet missing {missing}",
                )
            for entry in member["experience"]:
                for part in ("title", "detail"):
                    missing = [l for l in LANGS if not (entry[part].get(l) or "").strip()]
                    self.assertFalse(
                        missing, f"{member['id']} experience {part} missing {missing}",
                    )

    def test_contact_links_are_real_links(self) -> None:
        for member in self.out["members"]:
            self.assertGreaterEqual(
                len(member["links"]), 2, f"{member['id']} has almost no contacts",
            )
            for link in member["links"]:
                self.assertRegex(
                    link["href"], r"^(https?://|mailto:)",
                    f"{member['id']} has a link that goes nowhere: {link}",
                )
                self.assertTrue(link["text"].strip())

    # ------------------------------------------------------------ book

    def test_the_books_limits_are_the_servers_limits(self) -> None:
        """The one place a two-sided rule can silently disagree."""
        self.assertEqual(
            self.out["journal"]["max_len"], MAX_TEXT_LENGTH,
            "the book lets someone type a page the server will refuse",
        )
        self.assertEqual(
            self.out["journal"]["moods"], list(MOODS),
            "the book offers a mood the server does not accept",
        )

    # ------------------------------------------------------- the page

    def test_the_about_page_loads_the_project_sections(self) -> None:
        for asset in (
            "assets/css/about.css",
            "assets/js/about/about-roadmap.js",
            "assets/js/about/about-team.js",
        ):
            self.assertIn(asset, ABOUT_HTML, f"about.html does not load {asset}")
        for container in ("aboutRoadmap", "aboutTeam"):
            self.assertIn(f'id="{container}"', ABOUT_HTML)

    def test_the_reader_s_own_sections_left_the_about_page(self) -> None:
        """The whole point of the move. A book filed under "About us" is
        a book nobody finds, so About must not still be rendering it."""
        for stray in ("aboutJournal", "aboutPersonal", "about-journal.js",
                      "about-personal.js"):
            self.assertNotIn(
                stray, ABOUT_HTML,
                f"about.html still carries {stray} - the section was "
                f"supposed to move to you.html, not be copied",
            )

    def test_the_you_page_loads_both_of_them(self) -> None:
        for asset in (
            "assets/css/about.css",
            "assets/js/about/about-journal.js",
            "assets/js/about/about-personal.js",
            # The dossier prints field names, and without this table it
            # prints raw column names instead of what the app calls them.
            "assets/js/coach/coach-labels.js",
        ):
            self.assertIn(asset, YOU_HTML, f"you.html does not load {asset}")
        for container in ("aboutJournal", "aboutPersonal"):
            self.assertIn(f'id="{container}"', YOU_HTML)

    def test_the_you_page_is_reachable_from_the_nav(self) -> None:
        """A page nothing links to is a page nobody opens."""
        for page in ("about.html", "dashboard.html", "you.html", "weekly.html"):
            html = (ROOT / "frontend" / page).read_text(encoding="utf-8")
            self.assertIn('data-page="you"', html, f"{page} has no link to it")
            self.assertIn('href="you.html"', html, f"{page} has no link to it")

    def test_the_book_only_mounts_for_a_signed_in_account(self) -> None:
        """It is per-account and every call needs a token. Mounting it
        unconditionally fires a 401 on any anonymous load of this page."""
        # Both per-account sections mount inside the same `if (account)`
        # block; the regex spans it rather than pinning one call site,
        # so adding a third does not silently escape the guard.
        self.assertRegex(
            YOU_HTML,
            r"if \(account\)\s*\{[^}]*DWAboutJournal\.init",
            "the journal is mounted without checking there is an account",
        )
        self.assertRegex(
            YOU_HTML,
            r"if \(account\)\s*\{[^}]*DWAboutPersonal\.init",
            "the dossier is mounted without checking there is an account",
        )

    def test_the_sections_are_reachable_by_the_guide(self) -> None:
        guide = (ROOT / "frontend" / "assets" / "js" / "guide/guide-tips.js").read_text(encoding="utf-8")
        for topic, html in (("about_roadmap", ABOUT_HTML), ("about_team", ABOUT_HTML),
                            ("about_journal", YOU_HTML), ("about_personal", YOU_HTML)):
            self.assertIn(f'data-guide="{topic}"', html)
            for lang in LANGS:
                # Four copies, one per language block.
                self.assertGreaterEqual(
                    guide.count(f"{topic}:"), 5,  # 4 copy + 1 metadata
                    f"{topic} is not explained in every language",
                )

    def test_each_page_tour_visits_the_sections_that_page_actually_has(self) -> None:
        """A tour that stops on a section the page no longer renders
        leaves the guide talking to an empty screen."""
        guide = (ROOT / "frontend" / "assets" / "js" / "guide/guide-tips.js").read_text(encoding="utf-8")
        for tour_key, html, expected in (
            ("about", ABOUT_HTML, ("about_roadmap", "about_team")),
            ("you", YOU_HTML, ("about_journal", "about_personal")),
        ):
            match = re.search(rf"^    {tour_key}: \[(.*?)\],$", guide, re.M)
            self.assertIsNotNone(match, f"no page tour named {tour_key}")
            stops = re.findall(r"'([a-z_]+)'", match.group(1))
            for topic in expected:
                self.assertIn(topic, stops, f"the {tour_key} tour skips {topic}")
            for stop in stops:
                if stop == tour_key:
                    continue  # the page-level topic, not a section
                self.assertIn(
                    f'data-guide="{stop}"', html,
                    f"the {tour_key} tour stops on {stop}, which that page "
                    f"does not render",
                )

    def test_the_layout_is_written_in_logical_properties(self) -> None:
        """Persian and Arabic flip the whole page. A physical `left`
        that should have been `inset-inline-start` is invisible in
        English and breaks the layout in two of the four languages.
        The two exceptions are the book's hinge and its turn axis, which
        genuinely need a side and say so under html[dir="rtl"].
        """
        stripped = re.sub(r"/\*.*?\*/", "", ABOUT_CSS, flags=re.S)
        offenders = []
        for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", stripped):
            selector, body = rule.group(1).strip(), rule.group(2)
            if 'dir="rtl"' in selector:
                continue
            for prop in re.findall(r"(?:^|;)\s*(margin-left|margin-right|padding-left|padding-right|left|right)\s*:", body):
                if "transform-origin" in body:
                    continue
                offenders.append(f"{selector.splitlines()[-1].strip()} -> {prop}")
        self.assertFalse(
            offenders, f"physical side properties outside an rtl rule: {offenders[:6]}",
        )


if __name__ == "__main__":
    unittest.main()
