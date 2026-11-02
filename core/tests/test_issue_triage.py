import json
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "bin" / "check-intentable-result"

COMPLETE_TRIAGE = {
    "labels": ["type:feature", "clarity:2", "risk:2", "blast:2", "size:M"],
    "state": "needs-info",
    "message": "Should the venue page show past shows as well as upcoming ones?",
}


def run_checker(workflow, result=None, raw=None):
    """runs the checker on a result in a fresh folder; returns (exit status, output)"""
    with tempfile.TemporaryDirectory() as folder:
        if result is not None or raw is not None:
            target = Path(folder) / ".intentable" / "result.json"
            target.parent.mkdir()
            target.write_text(raw if raw is not None else json.dumps(result))
        done = subprocess.run(
            [sys.executable, str(CHECKER), workflow], cwd=folder, capture_output=True, text=True, timeout=30
        )
    return done.returncode, done.stdout + done.stderr


def triage(**changes):
    """an otherwise complete triage result"""
    return {**COMPLETE_TRIAGE, **changes}


class ResultsTheBridgeWouldRefuseTestCase(SimpleTestCase):
    """results the bridge would refuse fail the run"""

    def test_no_result_file(self):
        status, output = run_checker("triage")
        self.assertEqual(status, 1)
        self.assertIn("result is missing", output)

    def test_a_label_the_bridge_doesnt_know(self):
        for label in ("type:question", "state:building"):
            status, output = run_checker("triage", triage(labels=COMPLETE_TRIAGE["labels"] + [label]))
            self.assertEqual(status, 1, label)
            self.assertIn(label, output)

    def test_not_json(self):
        status, output = run_checker("triage", raw="labels: type:bug")
        self.assertEqual(status, 1)
        self.assertIn("isn't JSON", output)

    def test_the_label_list_is_unchanged(self):
        """a change detector: the checker's copy of the bridge's issue labels (bridge/src/labels.ts)"""
        namespace = {}
        exec(compile(CHECKER.read_text(), str(CHECKER), "exec"), namespace)
        self.assertEqual(
            namespace["ISSUE_LABELS"],
            ["type:bug", "type:feature", "type:refactor", "type:chore", "type:spike"]
            + [f"clarity:{n}" for n in range(1, 6)]
            + [f"risk:{n}" for n in range(1, 6)]
            + [f"blast:{n}" for n in range(1, 6)]
            + ["size:XS", "size:S", "size:M", "size:L", "size:XL"]
            + [f"P{n}" for n in range(1, 6)]
            + ["needs-design", "ai-shippable"],
        )


class LaterStageLabelsTestCase(SimpleTestCase):
    """labels for later stages are refused"""

    def test_a_label_for_a_later_stage(self):
        for workflow in ("triage", "clarify"):
            for label in ("ai-shippable", "needs-design", "P2"):
                status, output = run_checker(workflow, triage(labels=COMPLETE_TRIAGE["labels"] + [label]))
                self.assertEqual(status, 1, (workflow, label))
                self.assertIn(label, output)


class TriageLabelsTestCase(SimpleTestCase):
    """triage gives first-guess labels"""

    def test_a_complete_triage_result(self):
        status, output = run_checker("triage", COMPLETE_TRIAGE)
        self.assertEqual(status, 0, output)

    def test_a_triage_result_missing_a_group(self):
        status, output = run_checker("triage", triage(labels=["type:feature", "clarity:2", "risk:2", "blast:2"]))
        self.assertEqual(status, 1)
        self.assertIn("size", output)

    def test_two_labels_of_one_group(self):
        status, output = run_checker("triage", triage(labels=COMPLETE_TRIAGE["labels"] + ["type:bug"]))
        self.assertEqual(status, 1)
        self.assertIn("type", output)

    def test_parked_with_any_clarity(self):
        for clarity in ("clarity:2", "clarity:5"):
            labels = ["type:feature", clarity, "risk:2", "blast:2", "size:M"]
            message = "This may not belong in the site's spec, so Nate will decide."
            status, output = run_checker("triage", triage(labels=labels, state="parked", message=message))
            self.assertEqual(status, 0, output)


class ClarifyTestCase(SimpleTestCase):
    """clarify judges clarity afresh"""

    def test_clarify_asks_again(self):
        result = {
            "labels": ["clarity:3"],
            "state": "needs-info",
            "message": "Should artists see the venue's booking email, or a contact form?",
        }
        status, output = run_checker("clarify", result)
        self.assertEqual(status, 0, output)

    def test_clarify_cant_park(self):
        result = {"labels": ["clarity:3"], "state": "parked", "message": "Nate will decide whether this belongs."}
        status, output = run_checker("clarify", result)
        self.assertEqual(status, 1)
        self.assertIn("parked", output)

    def test_clarify_needs_a_clarity_label(self):
        status, output = run_checker("clarify", {"labels": [], "state": "needs-info", "message": "Which page?"})
        self.assertEqual(status, 1)
        self.assertIn("clarity", output)


class ClarityDecidesTheNextStepTestCase(SimpleTestCase):
    """clarity decides the next step"""

    def test_unclear_but_written_up(self):
        labels = ["type:feature", "clarity:3", "risk:2", "blast:2", "size:M"]
        status, output = run_checker("triage", triage(labels=labels, state="spec-review", message="A venue page."))
        self.assertEqual(status, 1)
        self.assertIn("clarity 3 needs a question", output)

    def test_clear_but_asking(self):
        labels = ["type:feature", "clarity:4", "risk:2", "blast:2", "size:M"]
        status, output = run_checker("triage", triage(labels=labels))
        self.assertEqual(status, 1)
        self.assertIn("clarity 4 goes to spec review", output)


class OneQuestionTestCase(SimpleTestCase):
    """one question at a time"""

    def test_two_questions_at_once(self):
        status, output = run_checker("triage", triage(message="Which page? And should it show past shows?"))
        self.assertEqual(status, 1)
        self.assertIn("ask one question", output)

    def test_no_question(self):
        status, output = run_checker("triage", triage(message="I need to know more about this."))
        self.assertEqual(status, 1)
        self.assertIn("ask one question", output)

    def test_no_message(self):
        for message in ("", "   ", None):
            result = triage(message=message) if message is not None else {k: v for k, v in COMPLETE_TRIAGE.items() if k != "message"}
            status, output = run_checker("triage", result)
            self.assertEqual(status, 1, repr(message))
            self.assertIn("message is missing", output)


class MessagesStayOnTheIssueTestCase(SimpleTestCase):
    """messages stay on the issue"""

    def test_a_mention(self):
        status, output = run_checker("triage", triage(message="Should @sooz see past shows too?"))
        self.assertEqual(status, 1)
        self.assertIn("mention no one", output)

    def test_an_email_address(self):
        labels = ["type:feature", "clarity:4", "risk:2", "blast:2", "size:M"]
        message = "A venue page with upcoming shows, and for artists the venue's booking address, booking@venue.com."
        status, output = run_checker("triage", triage(labels=labels, state="spec-review", message=message))
        self.assertEqual(status, 0, output)

    def test_too_long(self):
        labels = ["type:feature", "clarity:4", "risk:2", "blast:2", "size:M"]
        status, output = run_checker("triage", triage(labels=labels, state="spec-review", message="x" * 2001))
        self.assertEqual(status, 1)
        self.assertIn("too long", output)
