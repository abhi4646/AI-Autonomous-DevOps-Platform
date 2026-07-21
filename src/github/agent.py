import re

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
        return request_json(
            "GET",
            f"{self.repo_url()}/git/ref/heads/{branch_name}",
            headers=self.headers,
        )

    def create_branch(self, branch_name, source_branch="main"):
        if not self.ready():
            return {
                "status": "missing_config",
                "branch": branch_name,
            }

        source = self.get_branch(source_branch)
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