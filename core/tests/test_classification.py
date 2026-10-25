import json
from types import SimpleNamespace
from unittest import mock

from core.event_fetching import classification
from core.event_fetching.kinds import KINDS
from django.test import SimpleTestCase


def item(i):
    return {"title": f"Show {i}", "artists": "", "description": "", "venue": "The Venue"}


def reply(labels, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=json.dumps({"labels": labels}))],
        usage=SimpleNamespace(input_tokens=100, output_tokens=10),
    )


def labelling_client(kind="live_music"):
    """a client that labels every event in each request with `kind`"""
    client = mock.Mock()

    def create(**request):
        count = request["messages"][0]["content"].count("\n[") + 1
        return reply([{"index": i, "kind": kind} for i in range(count)])

    client.beta.messages.create.side_effect = create
    return client


class ClassifyTestCase(SimpleTestCase):
    def test_batches_of_fifty(self):
        client = labelling_client()
        kinds, errors, (input_tokens, _) = classification.classify(
            client, [item(i) for i in range(120)]
        )
        self.assertEqual(client.beta.messages.create.call_count, 3)
        self.assertEqual(kinds, ["live_music"] * 120)
        self.assertEqual(errors, [])
        self.assertEqual(input_tokens, 300)

    def test_request(self):
        client = labelling_client()
        classification.classify(
            client,
            [
                {
                    "title": "Halloween Bash",
                    "artists": "DJ Shakes",
                    "description": "costumes!\n" + "x" * 500,
                    "venue": "Aura (Portland, ME)",
                }
            ],
        )
        request = client.beta.messages.create.call_args.kwargs
        self.assertEqual(request["model"], "claude-haiku-5-5")
        schema = request["output_config"]["format"]["schema"]
        kind = schema["properties"]["labels"]["items"]["properties"]["kind"]
        self.assertEqual(kind["enum"], KINDS)
        content = request["messages"][0]["content"]
        self.assertIn("[0] Halloween Bash", content)
        self.assertIn("performers: DJ Shakes", content)
        self.assertIn("venue: Aura (Portland, ME)", content)
        # descriptions are shortened and flattened
        self.assertIn("description: costumes! xxx", content)
        self.assertLess(len(content), 500)
        # the party rule is in the prompt
        self.assertIn("only when a band, artist or DJ is named", request["system"])

    def test_missing_and_invalid_labels_are_unlabelled(self):
        client = mock.Mock()
        client.beta.messages.create.return_value = reply(
            [{"index": 0, "kind": "comedy"}, {"index": 2, "kind": "polka"}, {"index": 9, "kind": "other"}]
        )
        kinds, errors, _ = classification.classify(client, [item(i) for i in range(3)])
        self.assertEqual(kinds, ["comedy", "", ""])
        self.assertEqual(errors, [])

    def test_failed_batch_only_affects_its_own_events(self):
        client = labelling_client("other")
        good = client.beta.messages.create.side_effect

        def flaky(**request):
            if "[0] Show 50" in request["messages"][0]["content"]:
                raise ValueError("bad json")
            return good(**request)

        client.beta.messages.create.side_effect = flaky
        kinds, errors, _ = classification.classify(client, [item(i) for i in range(120)])
        self.assertEqual(kinds[:50], ["other"] * 50)
        self.assertEqual(kinds[50:100], [""] * 50)
        self.assertEqual(kinds[100:], ["other"] * 20)
        self.assertEqual(errors, ["labelling events 51-100 failed: bad json"])

    def test_cut_off_response_is_a_failure(self):
        client = mock.Mock()
        client.beta.messages.create.return_value = reply([], stop_reason="max_tokens")
        kinds, errors, _ = classification.classify(client, [item(0)])
        self.assertEqual(kinds, [""])
        self.assertIn("stopped with max_tokens", errors[0])

    def test_nothing_to_label(self):
        client = mock.Mock()
        self.assertEqual(classification.classify(client, []), ([], [], (0, 0)))
        client.beta.messages.create.assert_not_called()
