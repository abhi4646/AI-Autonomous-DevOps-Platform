import base64
import re

import requests

from src.agents import BaseAgent
from src.core.config import settings
from src.core.http import request_json


class GitHubAgent(BaseAgent):
    def __init__(self):
        super().__init__("GitHub Agent")

        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def ready(self):
        return all(
            [
                settings.github_token,
                settings.github_owner,
                settings.github_repo,
            ]
        )

    def repo_url(self):
        return (
            f"https://api.github.com/repos/"
            f"{settings.github_owner}/{settings.github_repo}"
        )

    def get_repo(self):
        if not self.ready():
            return {"status": "missing_config"}

        return request_json(
            "GET",
            self.repo_url(),
            headers=self.headers,
        )

    def get_branch(self, branch_name):
        if not self.ready():
            return None

        response = requests.get(
            f"{self.repo_url()}/git/ref/heads/{branch_name}",
            headers=self.headers,
            timeout=30,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    def branch_exists(self, branch_name):
        return self.get_branch(branch_name) is not None

    def create_branch(self, branch_name, source_branch="main"):
        if not self.ready():
            return {
                "status": "missing_config",
                "branch": branch_name,
            }

        # Safe rerun
        existing_branch = self.get_branch(branch_name)

        if existing_branch:
            return {
                "status": "already_exists",
                "branch": branch_name,
                "sha": existing_branch["object"]["sha"],
            }

        source = self.get_branch(source_branch)

        if not source:
            return {
                "status": "source_branch_not_found",
                "source_branch": source_branch,
            }

        source_sha = source["object"]["sha"]

        result = request_json(
            "POST",
            f"{self.repo_url()}/git/refs",
            headers=self.headers,
            json={
                "ref": f"refs/heads/{branch_name}",
                "sha": source_sha,
            },
        )

        return {
            "status": "created",
            "branch": branch_name,
            "source_branch": source_branch,
            "sha": result["object"]["sha"],
        }

    def create_or_update_file(
        self,
        branch_name,
        file_path,
        content,
        commit_message,
    ):
        """
        Creates a real commit on the Jira-generated branch.
        This gives GitHub something to include in a pull request.
        """

        if not self.ready():
            return {"status": "missing_config"}

        file_url = f"{self.repo_url()}/contents/{file_path}"

        existing_response = requests.get(
            file_url,
            headers=self.headers,
            params={"ref": branch_name},
            timeout=30,
        )

        payload = {
            "message": commit_message,
            "content": base64.b64encode(
                content.encode("utf-8")
            ).decode("utf-8"),
            "branch": branch_name,
        }

        if existing_response.status_code == 200:
            payload["sha"] = existing_response.json()["sha"]
        elif existing_response.status_code != 404:
            existing_response.raise_for_status()

        response = requests.put(
            file_url,
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        return {
            "status": "committed",
            "file": file_path,
            "branch": branch_name,
            "commit_sha": data["commit"]["sha"],
        }

    def find_open_pull_request(self, branch_name):
        response = requests.get(
            f"{self.repo_url()}/pulls",
            headers=self.headers,
            params={
                "state": "open",
                "head": f"{settings.github_owner}:{branch_name}",
            },
            timeout=30,
        )

        response.raise_for_status()

        pulls = response.json()

        if not pulls:
            return None

        return pulls[0]

    def create_pull_request(
        self,
        branch_name,
        title,
        body,
        base_branch="main",
    ):
        if not self.ready():
            return {"status": "missing_config"}

        existing = self.find_open_pull_request(branch_name)

        if existing:
            return {
                "status": "already_exists",
                "number": existing["number"],
                "url": existing["html_url"],
            }

        response = requests.post(
            f"{self.repo_url()}/pulls",
            headers=self.headers,
            json={
                "title": title,
                "body": body,
                "head": branch_name,
                "base": base_branch,
            },
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        return {
            "status": "created",
            "number": data["number"],
            "url": data["html_url"],
        }

    @staticmethod
    def make_branch_name(issue):
        issue_key = issue["key"].lower()
        summary = issue["summary"].lower()

        safe_summary = re.sub(r"[^a-z0-9]+", "-", summary)
        safe_summary = safe_summary.strip("-")

        return f"feature/{issue_key}-{safe_summary}"

    def execute(self, context=None):
        if not self.ready():
            return {
                "github": {
                    "status": "missing_config",
                }
            }

        repo = self.get_repo()

        return {
            "github": {
                "status": "connected",
                "repo": repo.get("full_name"),
                "default_branch": repo.get("default_branch"),
            }
        }