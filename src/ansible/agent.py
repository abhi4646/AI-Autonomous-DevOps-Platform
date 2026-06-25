import subprocess
from src.agents import BaseAgent
from src.core.config import settings
class AnsibleAgent(BaseAgent):
    def __init__(self): super().__init__('Ansible Agent')
    def run_playbook(self):
        if settings.app_mode=='dry_run': return {'status':'dry_run','command':f'ansible-playbook -i {settings.ansible_inventory_path} {settings.ansible_playbook_path}'}
        r=subprocess.run(['ansible-playbook','-i',settings.ansible_inventory_path,settings.ansible_playbook_path],capture_output=True,text=True); return {'status':'success' if r.returncode==0 else 'failed','stdout':r.stdout[-1500:],'stderr':r.stderr[-1500:]}
    def execute(self, context=None): return {'ansible': self.run_playbook()}
