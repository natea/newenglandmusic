"""
makes posthog's dashboard of how the site is used match core/analytics_dashboard.py
(add-analytics-dashboard): creates the dashboard and its charts, updates charts that changed,
deletes charts it made that are no longer defined, and deletes the wizard's empty dashboard.
run by hand, with a personal api key in .env (POSTHOG_PERSONAL_API_KEY, scoped to the project
with insight and dashboard read and write); never in the scheduled jobs:

    venv/bin/python manage.py sync_posthog_dashboard --dry-run
    venv/bin/python manage.py sync_posthog_dashboard

the charts it made are recognised by their tag and the key in their description's last line;
anything else in the project is left alone. the key goes only in the authorization header.
"""

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.analytics_dashboard import CHARTS, DASHBOARD, WIZARD_DASHBOARD

TAG = "stagehopper-dashboard"
KEY_LINE = "chart key: "
TIMEOUT = 30


class PostHogAPI:
    """the few project endpoints the sync uses, on posthog's app host"""

    def __init__(self, host, project_id, api_key, session=None):
        self.base = f"{host.rstrip('/')}/api/projects/{project_id}/"
        self.session = session or requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"

    def request(self, method, path, body=None):
        response = self.session.request(method, self.base + path, json=body, timeout=TIMEOUT)
        if not response.ok:
            try:
                message = response.json().get("detail") or response.text[:300]
            except ValueError:
                message = response.text[:300]
            raise CommandError(f"PostHog answered {response.status_code} to {method} {path}: {message}")
        return response.json() if response.content else {}

    def list(self, path):
        results, url = [], path
        while url:
            page = self.request("GET", url)
            results.extend(page.get("results", []))
            following = page.get("next")
            # posthog gives the next page as a full address on the same host
            url = following[len(self.base):] if following and following.startswith(self.base) else None
        return results

    def dashboards(self):
        return [d for d in self.list("dashboards/?limit=200") if not d.get("deleted")]

    def insights(self):
        return [i for i in self.list("insights/?saved=true&limit=200") if not i.get("deleted")]

    def create(self, kind, body):
        return self.request("POST", f"{kind}/", body)

    def update(self, kind, item_id, body):
        return self.request("PATCH", f"{kind}/{item_id}/", body)

    def delete(self, kind, item_id):
        # posthog deletes by marking deleted
        return self.request("PATCH", f"{kind}/{item_id}/", {"deleted": True})


def chart_key(insight):
    """the key the sync wrote on an insight it made, or None"""
    if TAG not in (insight.get("tags") or []):
        return None
    last = (insight.get("description") or "").strip().splitlines()[-1:] or [""]
    return last[0][len(KEY_LINE):].strip() if last[0].startswith(KEY_LINE) else None


def chart_body(chart, dashboard_id):
    return {
        "name": chart["name"],
        "description": f"{chart['description']}\n\n{KEY_LINE}{chart['key']}",
        "query": chart["query"],
        "tags": [TAG],
        "dashboards": [dashboard_id] if dashboard_id else [],
    }


def covers(stored, wanted):
    """whether posthog's stored value has everything we set: it saves a chart with its own
    defaults filled in (version, legend, axis settings...), which aren't a change"""
    if isinstance(wanted, dict):
        return isinstance(stored, dict) and all(key in stored and covers(stored[key], value) for key, value in wanted.items())
    if isinstance(wanted, list):
        return isinstance(stored, list) and len(stored) == len(wanted) and all(map(covers, stored, wanted))
    return stored == wanted


def differs(insight, body):
    return (
        insight.get("name") != body["name"]
        or (insight.get("description") or "") != body["description"]
        or not covers(insight.get("query"), body["query"])
        or sorted(insight.get("dashboards") or []) != sorted(body["dashboards"])
    )


class Command(BaseCommand):
    help = "Make PostHog's dashboard of how the site is used match core/analytics_dashboard.py"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="print what would change, and change nothing")

    def handle(self, *args, dry_run=False, **options):
        for name in ("POSTHOG_PERSONAL_API_KEY", "POSTHOG_PROJECT_ID", "POSTHOG_APP_HOST"):
            if not getattr(settings, name, ""):
                raise CommandError(f"{name} isn't set: the sync needs it (see PRODUCTION.md, \"Analytics\")")
        api = PostHogAPI(settings.POSTHOG_APP_HOST, settings.POSTHOG_PROJECT_ID, settings.POSTHOG_PERSONAL_API_KEY)
        self.sync(api, dry_run)

    def say(self, dry_run, text):
        self.stdout.write(("would " if dry_run else "") + text)

    def sync(self, api, dry_run):
        dashboards = api.dashboards()
        insights = api.insights()

        # the wizard's dashboard, and the charts that were only on it
        for wizard in [d for d in dashboards if d.get("name") == WIZARD_DASHBOARD]:
            for insight in insights:
                if (insight.get("dashboards") or []) == [wizard["id"]] and not chart_key(insight):
                    self.say(dry_run, f"delete the wizard's chart \"{insight.get('name')}\"")
                    if not dry_run:
                        api.delete("insights", insight["id"])
            self.say(dry_run, f"delete the dashboard \"{WIZARD_DASHBOARD}\"")
            if not dry_run:
                api.delete("dashboards", wizard["id"])

        ours = next((d for d in dashboards if d.get("name") == DASHBOARD["name"]), None)
        if ours is None:
            self.say(dry_run, f"create the dashboard \"{DASHBOARD['name']}\"")
            ours = {"id": None} if dry_run else api.create("dashboards", dict(DASHBOARD))
        elif (ours.get("description") or "") != DASHBOARD["description"]:
            self.say(dry_run, "update the dashboard's description")
            if not dry_run:
                api.update("dashboards", ours["id"], {"description": DASHBOARD["description"]})

        made = {key: insight for insight in insights if (key := chart_key(insight))}
        defined = {chart["key"] for chart in CHARTS}
        changed = 0
        for chart in CHARTS:
            body = chart_body(chart, ours["id"])
            existing = made.get(chart["key"])
            if existing is None:
                self.say(dry_run, f"create the chart \"{chart['name']}\"")
                changed += 1
                if not dry_run:
                    api.create("insights", body)
            elif differs(existing, body):
                self.say(dry_run, f"update the chart \"{chart['name']}\"")
                changed += 1
                if not dry_run:
                    api.update("insights", existing["id"], body)
        for key, insight in made.items():
            if key not in defined:
                self.say(dry_run, f"delete the chart \"{insight.get('name')}\", no longer defined")
                changed += 1
                if not dry_run:
                    api.delete("insights", insight["id"])
        if not changed:
            self.stdout.write("the charts are up to date")
