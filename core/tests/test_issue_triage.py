import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from core.tests.test_fabro_config import FABRO, workflow

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "bin" / "check-intentable-result"

NEXT = "Next, this will be written up as a proposal for Nate to review before anything is built."

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
        message = "A venue page with upcoming shows, and for artists the venue's booking address, booking@venue.com. " + NEXT
        status, output = run_checker("triage", triage(labels=labels, state="spec-review", message=message))
        self.assertEqual(status, 0, output)

    def test_too_long(self):
        labels = ["type:feature", "clarity:4", "risk:2", "blast:2", "size:M"]
        status, output = run_checker("triage", triage(labels=labels, state="spec-review", message="x" * 2001 + " " + NEXT))
        self.assertEqual(status, 1)
        self.assertIn("too long", output)


# the workflows' configuration

WORKFLOWS = ("triage", "clarify")
INPUTS = ["issue_number", "issue_title", "issue_body", "issue_author", "issue_thread"]
STATES = {"triage": ["spec-review", "needs-info", "parked"], "clarify": ["spec-review", "needs-info"]}
GROUPS = ["type:", "clarity:", "risk:", "blast:", "size:"]


def attribute(attrs, name):
    """a step attribute's quoted value, or None"""
    found = re.search(rf'(?<![\w.]){re.escape(name)}\s*=\s*"((?:[^"\\]|\\.)*)"', attrs)
    return found.group(1) if found else None


def prompt(name):
    return (FABRO / "workflows" / name / "prompt.md").read_text()


class WorkflowShapeTestCase(SimpleTestCase):
    """triage and clarify workflows exist"""

    def test_workflow_shape(self):
        for name in WORKFLOWS:
            settings, graph, steps, edges = workflow(name)
            self.assertEqual(edges, [" install -> think -> check "], name)
            install = attribute(steps["install"], "script")
            self.assertIn("@anthropic-ai/claude-code@2.1.316", install)
            self.assertIn("@agentclientprotocol/claude-agent-acp@0.99.1", install)
            self.assertIn("python3 --version", install)
            self.assertEqual(attribute(steps["think"], "type"), "agent")
            self.assertEqual(attribute(steps["think"], "backend"), "acp")
            self.assertEqual(attribute(steps["think"], "prompt"), "@prompt.md")
            self.assertEqual(attribute(steps["check"], "script"), f"python3 bin/check-intentable-result {name}")
            self.assertEqual(settings["workflow"]["graph"], "workflow.fabro")


class InputsTestCase(SimpleTestCase):
    """the workflows take the issue as inputs; issue text never reaches a command"""

    def test_inputs_declared_and_used(self):
        for name in WORKFLOWS:
            settings = workflow(name)[0]
            self.assertEqual(sorted(settings["run"]["inputs"]), sorted(INPUTS), name)
            for key in INPUTS:
                self.assertIn(f"{{{{ inputs.{key} }}}}", prompt(name), (name, key))

    def test_commands_without_inputs(self):
        for name in WORKFLOWS:
            for step, attrs in workflow(name)[2].items():
                script = attribute(attrs, "script")
                if script is not None:
                    self.assertNotIn("{{ inputs.", script, (name, step))


class NothingPushedTestCase(SimpleTestCase):
    """the workflows read the code and push nothing"""

    def test_nothing_pushed(self):
        for name in WORKFLOWS:
            run = workflow(name)[0]["run"]
            self.assertIs(run["pull_request"]["enabled"], False, name)
            self.assertIs(run["run_branch"]["push"], False, name)
            # GitHub permissions would replace the sandbox's read-only git access
            self.assertNotIn("integrations", run, name)


class RunEndsWithItsResultTestCase(SimpleTestCase):
    """a run ends with its result; the result is kept for the bridge"""

    def test_no_human_gate(self):
        for name in WORKFLOWS:
            graph = workflow(name)[1]
            self.assertNotIn("hexagon", graph, name)
            self.assertRegex(graph, r'(?m)^\s*on_failure="exit"\s*$')

    def test_result_collected_not_committed(self):
        for name in WORKFLOWS:
            self.assertEqual(workflow(name)[0]["run"]["artifacts"]["include"], [".intentable/result.json"], name)
        ignored = [line.strip() for line in (FABRO.parent / ".gitignore").read_text().splitlines()]
        self.assertIn(".intentable/", ignored)


class PromptRulesTestCase(SimpleTestCase):
    """the prompts state the rules"""

    def test_prompt_rules(self):
        for name in WORKFLOWS:
            text = prompt(name)
            for needed in ("explore stance", ".intentable/result.json", "<!-- intentable-bridge -->", "exactly one question", "Change no file", "4"):
                self.assertIn(needed, text, (name, needed))
            for group in GROUPS:
                self.assertIn(f"`{group}", text, (name, group))
            for state in STATES[name]:
                self.assertIn(f"`{state}`", text, (name, state))
        self.assertNotIn("`parked`", prompt("clarify"))
        self.assertIn("clarity is 4 or 5", prompt("triage"))
        self.assertIn("clarity is 4 or 5", prompt("clarify"))


class GuideTestCase(SimpleTestCase):
    """a guide explains the workflows"""

    def test_guide_sections(self):
        guide = (FABRO.parent / "docs" / "FABRO.md").read_text()
        headings = [line.lstrip("#").strip() for line in guide.splitlines() if line.startswith("#")]
        for name in WORKFLOWS:
            self.assertIn(name, headings)
        trials = [line for line in guide.splitlines() if line.startswith("fabro run") and ":triage" in line]
        self.assertEqual(len(trials), 1)
        self.assertIn("--environment daytona", trials[0])
        self.assertIn("--target natea/newenglandmusic@<branch>", trials[0])


class WhatHappensNextTestCase(SimpleTestCase):
    """a spec-review message says what happens next"""

    def test_spec_review_says_what_happens_next(self):
        labels = ["type:feature", "clarity:4", "risk:2", "blast:2", "size:M"]
        summary = "A page for each venue with its upcoming shows."
        status, output = run_checker("triage", triage(labels=labels, state="spec-review", message=summary))
        self.assertEqual(status, 1)
        self.assertIn(NEXT, output)
        status, output = run_checker("triage", triage(labels=labels, state="spec-review", message=f"{summary} {NEXT}"))
        self.assertEqual(status, 0, output)

    def test_the_prompts_give_the_sentence(self):
        for name in WORKFLOWS:
            self.assertIn(NEXT, prompt(name), name)
