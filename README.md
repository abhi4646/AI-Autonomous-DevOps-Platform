# AI Autonomous DevOps & SDLC Platform

A multi-agent AI DevOps platform connecting Jira, GitHub, Docker, Terraform, Kubernetes, Ansible, Monitoring, and an AI decision engine.

## Capabilities

- Real Jira API integration: list/create/move issues
- GitHub API connection scaffold
- Docker build automation scaffold
- Terraform plan automation scaffold
- Kubernetes health-check scaffold
- Ansible playbook automation scaffold
- Monitoring checks
- AI routing decision-engine scaffold
- GitHub Actions CI

## Run

```powershell
py -m pip install -r requirements.txt
py main.py
py -m pytest
```

Copy `.env.example` to `.env`. Never commit `.env`.
