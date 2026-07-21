class Orchestrator:
    def __init__(self):
        self.agents = []

    def register_agent(self, agent):
        self.agents.append(agent)

    def get_agent(self, agent_name):
        return next(
            (
                agent
                for agent in self.agents
                if agent.name == agent_name
            ),
            None,
        )

    def select_todo_issue(self, issues):
        return next(
            (
                issue
                for issue in issues
                if issue.get("status", "").lower() == "to do"
            ),
            None,
        )

    def run(self, context=None):
        results = {
            agent.name: agent.execute(context)
            for agent in self.agents
        }

        jira_result = results.get("Jira Agent", {})
        jira_issues = jira_result.get("jira", {}).get("issues", [])

        selected_issue = self.select_todo_issue(jira_issues)

        if not selected_issue:
            results["Automation"] = {
                "status": "no_todo_issue",
            }
            return results

        github_agent = self.get_agent("GitHub Agent")

        if github_agent is None:
            results["Automation"] = {
                "status": "github_agent_not_found",
            }
            return results

        branch_name = github_agent.make_branch_name(selected_issue)

        results["Automation"] = {
            "status": "dry_run",
            "selected_issue": selected_issue,
            "planned_branch": branch_name,
        }

        return results