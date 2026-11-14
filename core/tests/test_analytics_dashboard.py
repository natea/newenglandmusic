"""
the posthog dashboard's definitions and sync_posthog_dashboard (add-analytics-dashboard), against
an in-memory posthog: nothing is sent anywhere.
"""

import copy
from io import StringIO
from unittest import mock

from core.analytics_dashboard import CHARTS, DASHBOARD, POSTHOG_EVENTS, SITE_EVENTS, WIZARD_DASHBOARD, chart_events
from core.management.commands import sync_posthog_dashboard as sync
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

KEY = "phx_test_personal_key_do_not_print"


class FakePostHog:
    """dashboards and insights in memory, with the calls made to change them"""

    def __init__(self):
        self.items = {"dashboards": {}, "insights": {}}
        self.changes = []
        self.next_id = 1

    def add(self, kind, **fields):
        item = {"id": self.next_id, "deleted": False, **fields}
        self.next_id += 1
        self.items[kind][item["id"]] = item
        return item

    def dashboards(self):
        return [copy.deepcopy(d) for d in self.items["dashboards"].values() if not d["deleted"]]

    def insights(self):
        return [copy.deepcopy(i) for i in self.items["insights"].values() if not i["deleted"]]

    def create(self, kind, body):
        self.changes.append(("create", kind, body.get("name")))
        return self.add(kind, **copy.deepcopy(body))

    def update(self, kind, item_id, body):
        self.changes.append(("update", kind, self.items[kind][item_id].get("name")))
        self.items[kind][item_id].update(copy.deepcopy(body))
        return self.items[kind][item_id]

    def delete(self, kind, item_id):
        self.changes.append(("delete", kind, self.items[kind][item_id].get("name")))
        self.items[kind][item_id]["deleted"] = True


def run(api, dry_run=False, charts=None):
    out = StringIO()
    command = sync.Command(stdout=out)
    with mock.patch.object(sync, "CHARTS", charts if charts is not None else CHARTS):
        command.sync(api, dry_run)
    return out.getvalue()


class DefinitionsTestCase(SimpleTestCase):
    def test_charts_use_sent_events(self):
        keys = [chart["key"] for chart in CHARTS]
        self.assertEqual(len(keys), len(set(keys)))
        for chart in CHARTS:
            self.assertTrue(chart["name"] and chart["description"], chart["key"])
            self.assertEqual(chart["query"]["kind"], "InsightVizNode")
            self.assertTrue(chart_events(chart) <= SITE_EVENTS | POSTHOG_EVENTS, chart["key"])

    def test_every_site_event_is_charted(self):
        charted = set().union(*(chart_events(chart) for chart in CHARTS))
        # the unsave is shown only beside saves in posthog's own views; every other event has a chart
        self.assertEqual(SITE_EVENTS - charted, {"show_unsaved"})


class SyncTestCase(SimpleTestCase):
    def test_first_run(self):
        api = FakePostHog()
        run(api)
        self.assertEqual([d["name"] for d in api.dashboards()], [DASHBOARD["name"]])
        dashboard = api.dashboards()[0]["id"]
        self.assertEqual(len(api.insights()), len(CHARTS))
        self.assertTrue(all(i["dashboards"] == [dashboard] and sync.TAG in i["tags"] for i in api.insights()))

    def test_running_twice_changes_nothing(self):
        api = FakePostHog()
        run(api)
        api.changes.clear()
        self.assertIn("up to date", run(api))
        self.assertEqual(api.changes, [])

    def test_posthogs_own_defaults_arent_a_change(self):
        api = FakePostHog()
        run(api)
        # posthog stores each chart with its defaults filled in
        for insight in api.items["insights"].values():
            source = insight["query"]["source"]
            source["version"] = 4
            source["dateRange"]["explicitDate"] = False
            source.setdefault("trendsFilter", {})["showLegend"] = False
        api.changes.clear()
        run(api)
        self.assertEqual(api.changes, [])

    def test_a_chart_changed(self):
        api = FakePostHog()
        run(api)
        api.changes.clear()
        changed = copy.deepcopy(CHARTS)
        changed[0]["description"] = "A new question."
        run(api, charts=changed)
        self.assertEqual(api.changes, [("update", "insights", CHARTS[0]["name"])])

    def test_a_chart_removed(self):
        api = FakePostHog()
        foreign = api.add("insights", name="Someone's own chart", description="not ours", tags=[], dashboards=[])
        run(api)
        api.changes.clear()
        run(api, charts=CHARTS[1:])
        self.assertEqual(api.changes, [("delete", "insights", CHARTS[0]["name"])])
        self.assertFalse(api.items["insights"][foreign["id"]]["deleted"])

    def test_dry_run(self):
        api = FakePostHog()
        out = run(api, dry_run=True)
        self.assertEqual(api.changes, [])
        self.assertIn(f"would create the dashboard \"{DASHBOARD['name']}\"", out)
        self.assertEqual(out.count("would create the chart"), len(CHARTS))

    def test_the_wizards_dashboard(self):
        api = FakePostHog()
        wizard = api.add("dashboards", name=WIZARD_DASHBOARD)
        other = api.add("dashboards", name="Someone's dashboard")
        wizard_chart = api.add("insights", name="Event submissions", description="", tags=[], dashboards=[wizard["id"]])
        shared = api.add("insights", name="Shared chart", description="", tags=[], dashboards=[wizard["id"], other["id"]])
        run(api)
        self.assertTrue(api.items["dashboards"][wizard["id"]]["deleted"])
        self.assertTrue(api.items["insights"][wizard_chart["id"]]["deleted"])
        self.assertFalse(api.items["dashboards"][other["id"]]["deleted"])
        self.assertFalse(api.items["insights"][shared["id"]]["deleted"])


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self._body = status, body
        self.ok = status < 400
        self.content = b"x"
        self.text = str(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.calls = []
        self.responses = list(responses)

    def request(self, method, url, json=None, timeout=None):
        self.calls.append((method, url, json))
        return self.responses.pop(0)


class SecretTestCase(SimpleTestCase):
    @override_settings(POSTHOG_PERSONAL_API_KEY="")
    def test_no_key(self):
        with mock.patch.object(sync.requests, "Session") as session:
            with self.assertRaisesMessage(CommandError, "POSTHOG_PERSONAL_API_KEY isn't set"):
                call_command("sync_posthog_dashboard", stdout=StringIO())
        session.assert_not_called()

    def test_the_key_goes_only_in_the_authorization_header(self):
        session = FakeSession([FakeResponse(200, {"results": [], "next": None})])
        api = sync.PostHogAPI("https://us.posthog.com", "735651", KEY, session=session)
        api.dashboards()
        self.assertEqual(session.headers["Authorization"], f"Bearer {KEY}")
        for method, url, body in session.calls:
            self.assertNotIn(KEY, url)
            self.assertNotIn(KEY, str(body))
        self.assertTrue(session.calls[0][1].startswith("https://us.posthog.com/api/projects/735651/dashboards/"))

    def test_a_failed_request(self):
        session = FakeSession([FakeResponse(403, {"detail": "You don't have access to this project."})])
        api = sync.PostHogAPI("https://us.posthog.com", "735651", KEY, session=session)
        with self.assertRaises(CommandError) as raised:
            api.insights()
        message = str(raised.exception)
        self.assertIn("403", message)
        self.assertIn("You don't have access to this project.", message)
        self.assertNotIn(KEY, message)

    def test_following_pages(self):
        base = "https://us.posthog.com/api/projects/735651/"
        session = FakeSession([
            FakeResponse(200, {"results": [{"id": 1, "name": "A"}], "next": base + "insights/?saved=true&limit=200&offset=200"}),
            FakeResponse(200, {"results": [{"id": 2, "name": "B"}], "next": None}),
        ])
        api = sync.PostHogAPI("https://us.posthog.com", "735651", KEY, session=session)
        self.assertEqual([i["name"] for i in api.insights()], ["A", "B"])
