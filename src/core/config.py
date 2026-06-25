import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
@dataclass
class Settings:
    app_mode: str = os.getenv('APP_MODE','dry_run')
    jira_base_url: str = os.getenv('JIRA_BASE_URL','')
    jira_email: str = os.getenv('JIRA_EMAIL','')
    jira_api_token: str = os.getenv('JIRA_API_TOKEN','')
    jira_project_key: str = os.getenv('JIRA_PROJECT_KEY','')
    github_token: str = os.getenv('GITHUB_TOKEN','')
    github_owner: str = os.getenv('GITHUB_OWNER','')
    github_repo: str = os.getenv('GITHUB_REPO','')
    openai_api_key: str = os.getenv('OPENAI_API_KEY','')
    openai_model: str = os.getenv('OPENAI_MODEL','gpt-4.1-mini')
    docker_image_name: str = os.getenv('DOCKER_IMAGE_NAME','ai-autonomous-devops-platform')
    kubeconfig_path: str = os.getenv('KUBECONFIG_PATH','')
    kubernetes_namespace: str = os.getenv('KUBERNETES_NAMESPACE','default')
    terraform_working_dir: str = os.getenv('TERRAFORM_WORKING_DIR','terraform')
    terraform_auto_apply: bool = os.getenv('TERRAFORM_AUTO_APPLY','false').lower() == 'true'
    ansible_inventory_path: str = os.getenv('ANSIBLE_INVENTORY_PATH','ansible/inventory.ini')
    ansible_playbook_path: str = os.getenv('ANSIBLE_PLAYBOOK_PATH','ansible/playbook.yml')
settings = Settings()
