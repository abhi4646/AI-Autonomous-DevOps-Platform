from src.agents import BaseAgent
from src.core.config import settings
from src.core.http import request_json
class GitHubAgent(BaseAgent):
    def __init__(self): super().__init__('GitHub Agent'); self.headers={'Accept':'application/vnd.github+json','Authorization':f'Bearer {settings.github_token}','X-GitHub-Api-Version':'2022-11-28'}
    def ready(self): return all([settings.github_token,settings.github_owner,settings.github_repo])
    def repo_url(self): return f'https://api.github.com/repos/{settings.github_owner}/{settings.github_repo}'
    def get_repo(self): return request_json('GET', self.repo_url(), headers=self.headers) if self.ready() else {'status':'missing_config'}
    def execute(self, context=None):
        if not self.ready(): return {'github':{'status':'missing_config'}}
        r=self.get_repo(); return {'github':{'status':'connected','repo':r.get('full_name'),'default_branch':r.get('default_branch')}}
