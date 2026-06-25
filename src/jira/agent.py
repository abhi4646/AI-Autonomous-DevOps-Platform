from requests.auth import HTTPBasicAuth
from src.agents import BaseAgent
from src.core.config import settings
from src.core.http import request_json
class JiraAgent(BaseAgent):
    def __init__(self):
        super().__init__('Jira Agent'); self.base_url=settings.jira_base_url.rstrip('/')
        self.auth=HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        self.headers={'Accept':'application/json','Content-Type':'application/json'}
    def ready(self): return all([self.base_url, settings.jira_email, settings.jira_api_token, settings.jira_project_key])
    def list_issues(self, max_results=10):
        if not self.ready(): return []
        data=request_json('POST', f'{self.base_url}/rest/api/3/search', auth=self.auth, headers=self.headers, json={
            'jql': f'project = {settings.jira_project_key} ORDER BY created DESC',
            'maxResults': max_results,
            'fields':['summary','status','priority','assignee','issuetype']})
        return [{'key':i['key'],'summary':i['fields'].get('summary'),'status':i['fields'].get('status',{}).get('name'),'priority':(i['fields'].get('priority') or {}).get('name'),'assignee':(i['fields'].get('assignee') or {}).get('displayName'),'issue_type':i['fields'].get('issuetype',{}).get('name')} for i in data.get('issues',[])]
    def create_issue(self, summary, description, issue_type='Task'):
        if settings.app_mode=='dry_run': return {'status':'dry_run','action':'create_issue','summary':summary}
        payload={'fields':{'project':{'key':settings.jira_project_key},'summary':summary,'description':{'type':'doc','version':1,'content':[{'type':'paragraph','content':[{'type':'text','text':description}]}]},'issuetype':{'name':issue_type}}}
        return request_json('POST', f'{self.base_url}/rest/api/3/issue', auth=self.auth, headers=self.headers, json=payload)
    def transitions(self, issue_key): return request_json('GET', f'{self.base_url}/rest/api/3/issue/{issue_key}/transitions', auth=self.auth, headers=self.headers)
    def move_issue(self, issue_key, transition_name):
        available=self.transitions(issue_key).get('transitions',[]); match=next((t for t in available if t['name'].lower()==transition_name.lower()),None)
        if not match: return {'status':'not_found','available':[t['name'] for t in available]}
        if settings.app_mode=='dry_run': return {'status':'dry_run','action':'move_issue','issue':issue_key,'transition':transition_name}
        return request_json('POST', f'{self.base_url}/rest/api/3/issue/{issue_key}/transitions', auth=self.auth, headers=self.headers, json={'transition':{'id':match['id']}})
    def execute(self, context=None): return {'jira': {'status':'connected' if self.ready() else 'missing_config','issues': self.list_issues(5)}}
