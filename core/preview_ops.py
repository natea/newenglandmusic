"""
what bin/preview does for pull request previews (preview-environments), acting on the decisions
in core/preview_plan.py through three small clients: neon's api, GitHub's api, and the shell
(docker and gcloud). the tests hand `Previews` fakes that record the calls. nothing here
imports django, so the workflow runs it with the runner's own python.
"""

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone

from core import preview_plan as plan

REGION = "us-east1"
RUNTIME_ACCOUNT = "preview-runtime"


class LimitReached(Exception):
    """every preview slot holds an open pull request's preview"""


class Previews:
    def __init__(self, neon, github, shell, image_repository, log=print, now=None):
        self.neon = neon
        self.github = github
        self.shell = shell
        self.image_repository = image_repository
        self.log = log
        self.now = now or (lambda: datetime.now(timezone.utc))

    def image(self, number):
        return f"{self.image_repository}:{plan.branch_name(number)}"

    # deploying

    def deploy(self, number, by_hand=False):
        """builds, branches, migrates and deploys a pull request's preview, and tells GitHub"""
        pull = self.github.pull(number)
        if pull is None:
            self.log(f"pull request #{number} doesn't exist")
            return "skipped"
        if by_hand and pull["merged"]:
            self.log(f"pull request #{number} is merged, so it gets no preview")
            return "skipped"
        wanted, why = plan.wants_preview(pull, self.github.pull_files(number))
        if not wanted:
            self.log(f"no preview for pull request #{number}: {why}")
            return "skipped"
        image = self.image(number)
        self.shell.build(image)
        database_url = self.database(number)
        # a preview whose migrations no longer apply starts again on a fresh branch
        database_url = self.migrate(number, image, database_url)
        self.shell.manage(image, plan.preview_env(database_url), "set_preview_admin", secret="PREVIEW_ADMIN_PASSWORD_HASH")
        service = plan.service_name(number)
        # a service that exists keeps its address, so it is deployed once, with its address
        url = self.shell.service_url(service)
        self.shell.deploy(service, image, plan.preview_env(database_url, site_url=url), RUNTIME_ACCOUNT)
        if not url:
            url = self.shell.service_url(service)
            self.shell.set_site_url(service, url)
        deployment = self.github.create_deployment(plan.deployment_payload(number, pull["sha"]))
        self.github.set_status(deployment, plan.status_payload(url))
        self.log(f"the preview of pull request #{number} is up at {url}")
        return url

    def database(self, number):
        """the preview's own branch's address, making the branch from the base when it isn't there"""
        name = plan.branch_name(number)
        branches = self.neon.branches()
        if name not in branches:
            previews = {n for n in map(plan.preview_number, branches) if n}
            if len(previews) >= plan.MAX_PREVIEWS:
                evicted = plan.to_evict(previews, self.pulls(previews))
                if evicted is None:
                    raise LimitReached(f"the limit of {plan.MAX_PREVIEWS} previews is reached; merge or close a pull request to free one")
                self.log(f"every slot is taken: removing the preview of pull request #{evicted}, closed without merging")
                self.remove(evicted)
            self.neon.create_branch(name)
        return self.neon.connection_url(name)

    def migrate(self, number, image, database_url):
        """the pull request's migrations on its branch; on failure, once more on a fresh copy of the base"""
        try:
            self.shell.manage(image, plan.preview_env(database_url), "migrate", "--no-input")
            return database_url
        except subprocess.CalledProcessError:
            self.log(f"the migrations failed on the kept database of pull request #{number}; starting again from the base, which loses what was saved on the preview")
        name = plan.branch_name(number)
        self.neon.delete_branch(name)
        self.neon.create_branch(name)
        fresh = self.neon.connection_url(name)
        self.shell.manage(image, plan.preview_env(fresh), "migrate", "--no-input")
        return fresh

    # removing

    def closed(self, number):
        """a closed pull request: merged, its preview goes; closed without merging, it stays"""
        pull = self.github.pull(number)
        if pull is not None and not pull["merged"]:
            self.log(f"pull request #{number} was closed without merging: its preview stays until its slot is needed")
            return "kept"
        self.remove(number)
        return "removed"

    def remove(self, number):
        """deletes a preview's service, database and image, and marks its deployments inactive"""
        service = plan.service_name(number)
        self.shell.delete_service(service)
        self.neon.delete_branch(plan.branch_name(number))
        self.shell.delete_image(self.image(number))
        for deployment in self.github.deployments(service):
            self.github.set_status(deployment, plan.INACTIVE)
        self.log(f"removed the preview of pull request #{number}")

    def pulls(self, numbers):
        """{number: state, merged and last push} for the pull requests that still exist"""
        found = {}
        for number in numbers:
            pull = self.github.pull(number)
            if pull is not None:
                found[number] = {"state": pull["state"], "merged": pull["merged"], "pushed_at": self.github.pushed_at(pull["sha"])}
        return found

    def sweep(self, everything=False):
        """removes previews whose pull request is merged or gone, and open ones idle for 7 days"""
        previews = {n for n in map(plan.preview_number, [*self.shell.services(), *self.neon.branches()]) if n}
        gone = sorted(previews) if everything else plan.to_sweep(previews, self.pulls(previews), self.now())
        for number in gone:
            self.remove(number)
        self.log(f"swept {len(gone)} of {len(previews)} previews")
        return gone


# the real clients


class Api:
    def __init__(self, base, token, headers=None):
        self.base = base
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json", **(headers or {})}

    def call(self, method, path, body=None, missing_ok=False):
        request = urllib.request.Request(self.base + path, method=method, headers=self.headers, data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                text = response.read().decode()
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            # the address may hold a password, so only the path is named
            raise RuntimeError(f"{method} {path.split('?')[0]} answered {error.code}") from None


class Neon:
    """the previews' neon project: one branch per preview, each a child of `base`"""

    BASE = "base"

    def __init__(self, api_key, project, database, role):
        self.api = Api("https://console.neon.tech/api/v2", api_key)
        self.project = project
        self.database = database
        self.role = role

    def _branches(self):
        return {b["name"]: b["id"] for b in self.api.call("GET", f"/projects/{self.project}/branches")["branches"]}

    def branches(self):
        return sorted(self._branches())

    def create_branch(self, name):
        ids = self._branches()
        body = {
            "branch": {"name": name, "parent_id": ids[self.BASE]},
            # the smallest compute, which sleeps when idle, so previews share the free hours
            "endpoints": [{"type": "read_write", "autoscaling_limit_min_cu": 0.25, "autoscaling_limit_max_cu": 0.25}],
        }
        self.api.call("POST", f"/projects/{self.project}/branches", body)

    def delete_branch(self, name):
        branch = self._branches().get(name)
        if branch and name != self.BASE:
            self.api.call("DELETE", f"/projects/{self.project}/branches/{branch}", missing_ok=True)

    def connection_url(self, name):
        branch = self._branches()[name]
        # a direct connection, never neon's pooler: the pooler hands one session's settings to
        # the next, and a restore leaves an empty search_path behind, which hides every table
        query = f"branch_id={branch}&database_name={self.database}&role_name={self.role}&pooled=false"
        return self.api.call("GET", f"/projects/{self.project}/connection_uri?{query}")["uri"]


class GitHub:
    def __init__(self, token, repository=plan.REPOSITORY):
        self.api = Api(f"https://api.github.com/repos/{repository}", token, {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})

    def pull(self, number):
        found = self.api.call("GET", f"/pulls/{number}", missing_ok=True)
        if found is None:
            return None
        return {
            "state": found["state"],
            "merged": bool(found.get("merged")),
            "sha": found["head"]["sha"],
            "base": found["base"]["ref"],
            "author": found["user"]["login"],
            "head_repository": (found["head"].get("repo") or {}).get("full_name"),
        }

    def pull_files(self, number):
        files = []
        for page in range(1, 31):
            batch = self.api.call("GET", f"/pulls/{number}/files?per_page=100&page={page}")
            files += [f["filename"] for f in batch]
            if len(batch) < 100:
                break
        return files

    def pushed_at(self, sha):
        when = self.api.call("GET", f"/commits/{sha}")["commit"]["committer"]["date"]
        return datetime.fromisoformat(when.replace("Z", "+00:00"))

    def create_deployment(self, payload):
        return self.api.call("POST", "/deployments", payload)["id"]

    def set_status(self, deployment, payload):
        self.api.call("POST", f"/deployments/{deployment}/statuses", payload)

    def deployments(self, environment):
        return [d["id"] for d in self.api.call("GET", f"/deployments?environment={environment}&per_page=100")]


class Shell:
    """docker and gcloud on the runner; secrets go in through the environment, never the command line"""

    def __init__(self, project, region=REGION):
        self.project = project
        self.region = region

    def run(self, *command, env=None, capture=False):
        result = subprocess.run(command, check=True, text=True, capture_output=capture, env={**os.environ, **(env or {})})
        return result.stdout.strip() if capture else ""

    def gcloud(self, *args, capture=False):
        return self.run("gcloud", *args, "--project", self.project, "--quiet", capture=capture)

    def build(self, image):
        self.run("docker", "build", "--tag", image, ".")
        self.run("docker", "push", image)

    def manage(self, image, env, *command, secret=None):
        """a management command from the image, against the preview's database"""
        passed = {**env, **({secret: os.environ[secret]} if secret else {})}
        names = [arg for name in passed for arg in ("--env", name)]
        self.run("docker", "run", "--rm", *names, image, "python", "manage.py", *command, env=passed)

    def service_url(self, service):
        try:
            return self.gcloud("run", "services", "describe", service, "--region", self.region, "--format", "value(status.url)", capture=True) or None
        except subprocess.CalledProcessError:
            return None

    def deploy(self, service, image, env, account):
        path = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), f"{service}.env.json")
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as file:
            json.dump(env, file)
        try:
            self.gcloud(
                "run", "deploy", service, "--image", image, "--region", self.region,
                "--service-account", f"{account}@{self.project}.iam.gserviceaccount.com",
                "--env-vars-file", path, "--allow-unauthenticated",
                "--min-instances", "0", "--max-instances", "1", "--memory", "512Mi", "--cpu", "1",
            )
        finally:
            os.remove(path)

    def set_site_url(self, service, url):
        self.gcloud("run", "services", "update", service, "--region", self.region, "--update-env-vars", f"SITE_URL={url}")

    def services(self):
        return self.gcloud("run", "services", "list", "--region", self.region, "--format", "value(metadata.name)", capture=True).split()

    def delete_service(self, service):
        if self.service_url(service):
            self.gcloud("run", "services", "delete", service, "--region", self.region)

    def delete_image(self, image):
        try:
            self.gcloud("artifacts", "docker", "images", "delete", image, "--delete-tags", capture=True)
        except subprocess.CalledProcessError:
            pass  # never built, or already gone
