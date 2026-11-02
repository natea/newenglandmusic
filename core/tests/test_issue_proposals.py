import re
from pathlib import Path

from django.test import SimpleTestCase

from core.tests.test_fabro_config import FABRO, read_toml
from core.tests.test_issue_triage import INPUTS, attribute

ROOT = Path(__file__).resolve().parents[2]
SPEC = FABRO / "workflows" / "spec"
AGENTS = ("propose", "sketch", "risk", "spec_fit", "fidelity", "revise")
REVIEWERS = {"risk": "risk", "spec_fit": "spec fit", "fidelity": "fidelity"}


def graph():
    """the spec graph's text, its steps by name, and its edges as (from, to, condition)"""
    text = (SPEC / "workflow.fabro").read_text()
    body = re.sub(r"(?m)^\s*//.*$", "", text)
    steps = {
        node: attrs
        for node, attrs in re.findall(r"^\s*(\w+)\s*\[(.*?)\]\s*$", body, re.MULTILINE | re.DOTALL)
        if node != "graph"
    }
    edges = []
    for line in body.splitlines():
        if "->" not in line:
            continue
        chain, _, rest = line.partition("[")
        nodes = [n.strip() for n in chain.split("->")]
        condition = attribute(rest, "condition") if rest else None
        edges += [(a, b, condition) for a, b in zip(nodes, nodes[1:])]
    return text, steps, edges


def settings():
    return read_toml(SPEC / "workflow.toml")


def prompt(name):
    return (SPEC / f"{name}.md").read_text()


def next_steps(edges, node):
    return {(b, c) for a, b, c in edges if a == node}


class WorkflowShapeTestCase(SimpleTestCase):
    """a spec workflow exists; a proposal that needs screens includes sketches; every agent runs through ACP"""

    def test_workflow_shape(self):
        text, steps, edges = graph()
        install = attribute(steps["install"], "script")
        for pinned in (
            "@anthropic-ai/claude-code@2.1.316",
            "@agentclientprotocol/claude-agent-acp@0.99.1",
            "@fission-ai/openspec@1.16.0",
            "--branch skill-v4.8.0 https://github.com/pbakaus/impeccable",
        ):
            self.assertIn(pinned, install)
        self.assertEqual(next_steps(edges, "start"), {("install", None)})
        self.assertEqual(next_steps(edges, "install"), {("propose", None)})
        self.assertEqual(attribute(steps["propose"], "prompt"), "@propose.md")
        self.assertEqual(next_steps(edges, "propose"), {("check_draft", None)})
        self.assertEqual(
            attribute(steps["check_draft"], "script"),
            "python3 bin/check-intentable-result spec --draft",
        )
        self.assertEqual(next_steps(edges, "check_draft"), {("route", None)})
        self.assertRegex(steps["fork"], r"\bshape=component\b")
        self.assertEqual(next_steps(edges, "fork"), {(r, None) for r in REVIEWERS})
        for reviewer in REVIEWERS:
            self.assertEqual(attribute(steps[reviewer], "prompt"), f"@{reviewer}.md")
            self.assertEqual(next_steps(edges, reviewer), {("merge", None)})
        self.assertRegex(steps["merge"], r"\bshape=tripleoctagon\b")
        self.assertEqual(next_steps(edges, "merge"), {("check_reviews", None)})
        self.assertEqual(
            next_steps(edges, "check_reviews"),
            {("finish", "context.review_done=true"), ("revise", None)},
        )
        self.assertEqual(attribute(steps["revise"], "prompt"), "@revise.md")
        self.assertEqual(next_steps(edges, "revise"), {("recheck", None)})
        self.assertEqual(
            attribute(steps["recheck"], "script"),
            "python3 bin/check-intentable-result spec --draft",
        )
        self.assertEqual(next_steps(edges, "recheck"), {("fork", None)})
        self.assertEqual(
            attribute(steps["finish"], "script"),
            "python3 bin/check-intentable-result spec",
        )
        self.assertEqual(next_steps(edges, "finish"), {("exit", None)})
        self.assertEqual(settings()["workflow"]["graph"], "workflow.fabro")

    def test_sketch_step_only_for_needs_design(self):
        text, steps, edges = graph()
        self.assertEqual(attribute(steps["route"], "output_schema"), "routing")
        self.assertEqual(
            next_steps(edges, "route"),
            {
                ("sketch", "context.route=sketch"),
                ("finish", "context.route=back"),
                ("fork", None),
            },
        )
        self.assertEqual(attribute(steps["sketch"], "prompt"), "@sketch.md")
        self.assertEqual(next_steps(edges, "sketch"), {("check_sketches", None)})
        self.assertEqual(
            attribute(steps["check_sketches"], "script"),
            "python3 bin/check-intentable-result spec --sketches",
        )
        self.assertEqual(next_steps(edges, "check_sketches"), {("fork", None)})
        # the revise loop never reaches the sketch step
        self.assertNotIn(
            "sketch",
            {b for a, b, c in edges if a in ("revise", "recheck", "check_reviews")},
        )

    def test_every_agent_through_acp(self):
        text, steps, edges = graph()
        agents = {name for name, attrs in steps.items() if attribute(attrs, "type") == "agent"}
        self.assertEqual(agents, set(AGENTS))
        for name in AGENTS:
            self.assertEqual(attribute(steps[name], "backend"), "acp", name)
            self.assertEqual(attribute(steps[name], "acp.command"), "claude-agent-acp", name)
        # every other step is a script or a structural node, never a prompt stage
        for name, attrs in steps.items():
            if name not in AGENTS:
                self.assertIsNone(attribute(attrs, "prompt"), name)


class WorkflowContractTestCase(SimpleTestCase):
    """the spec workflow follows the workflow contract"""

    def test_inputs_used_commands_without_inputs(self):
        self.assertEqual(sorted(settings()["run"]["inputs"]), sorted(INPUTS))
        for key in INPUTS:
            self.assertIn(f"{{{{ inputs.{key} }}}}", prompt("propose"), key)
        for name, attrs in graph()[1].items():
            script = attribute(attrs, "script")
            if script is not None:
                self.assertNotIn("{{ inputs.", script, name)

    def test_no_gate_no_children_references_inside(self):
        text, steps, edges = graph()
        self.assertRegex(text, r'(?m)^\s*on_failure="exit"\s*$')
        self.assertNotIn("hexagon", text)
        self.assertNotRegex(text, r"child_workflow\s*=")
        for reference in re.findall(r'"@([^"]+)"', text):
            self.assertTrue((SPEC / reference).is_file(), reference)
            self.assertNotIn("/", reference)


class NothingPushedTestCase(SimpleTestCase):
    """the spec workflow pushes nothing"""

    def test_nothing_pushed(self):
        run = settings()["run"]
        self.assertIs(run["pull_request"]["enabled"], False)
        self.assertIs(run["run_branch"]["push"], False)
        # GitHub permissions would replace the sandbox's read-only git access
        self.assertNotIn("integrations", run)
        self.assertEqual(
            run["artifacts"]["include"],
            [
                ".intentable/result.json",
                ".intentable/review.md",
                ".intentable/proposal/**",
            ],
        )


class ReviewerPromptsTestCase(SimpleTestCase):
    """reviewers are fresh, one lens each; the fidelity reviewer reads the decision record; reports only"""

    def test_three_lenses(self):
        named = {}
        for reviewer, lens in REVIEWERS.items():
            text = prompt(reviewer)
            self.assertIn(f"## Your lens: {lens}", text, reviewer)
            for other, other_lens in REVIEWERS.items():
                if other != reviewer:
                    self.assertNotIn(f"## Your lens: {other_lens}", text, reviewer)
            named[reviewer] = lens
        self.assertEqual(len(set(named.values())), 3)
        self.assertIn("readers the task list misses", prompt("risk"))
        self.assertIn("`openspec/config.yaml`", prompt("spec_fit"))
        self.assertIn("`AGENTS.md`", prompt("spec_fit"))
        self.assertIn("An unflagged one is blocking", prompt("fidelity"))

    def test_decision_record_and_bridge_comments(self):
        fidelity = prompt("fidelity")
        for needed in (
            "thread",
            "`AGENTS.md`",
            "`openspec/changes/archive/`",
            "{{ inputs.issue_thread }}",
        ):
            self.assertIn(needed, fidelity)
        for name in ("fidelity", "propose"):
            self.assertIn("<!-- intentable-bridge -->", prompt(name), name)
            self.assertIn("not the owner speaking", prompt(name), name)

    def test_reviewer_prompts(self):
        for reviewer in REVIEWERS:
            text = prompt(reviewer)
            self.assertIn(f"`.intentable/reviews/{reviewer}.md`", text, reviewer)
            for heading in (
                "SATISFIED: yes|no",
                "BLOCKING:",
                "NON-BLOCKING:",
                "CONFIRMED OK:",
            ):
                self.assertIn(heading, text, (reviewer, heading))
            self.assertIn("`none` under an empty heading", text, reviewer)
            self.assertIn("Edit nothing else", text, reviewer)
            self.assertIn("`revise.md`", text, reviewer)

    def test_revise_prompt(self):
        text = prompt("revise")
        self.assertIn("Apply every blocking finding", text)
        self.assertIn("`.intentable/reviews/revise.md`", text)
        self.assertIn("do not rename the change", text)
        self.assertIn("Do not change its `labels`", text)
        self.assertIn("nothing under `.intentable/proposal/`", text)


class ProposePromptTestCase(SimpleTestCase):
    """the proposal prompt states the rules"""

    def test_the_prompt_gives_the_rules(self):
        text = prompt("propose")
        for needed in (
            "planning artifacts only",
            "`openspec/config.yaml`",
            "`AGENTS.md`",
            "Keep host and network names out",
            "open question",
            "two to four plain sentences",
            "no @-mentions",
            "`.intentable/draft.json`",
            "`needs-info`",
            "exactly one question",
        ):
            self.assertIn(needed, text, needed)

    def test_sketch_prompt_rules(self):
        text = prompt("sketch")
        for needed in (
            "system fonts only",
            "No scripts",
            "nothing loaded from another address",
            "`options.json`",
            "Do not generate images",
        ):
            self.assertIn(needed, text, needed)
