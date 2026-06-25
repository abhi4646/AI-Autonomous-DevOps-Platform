import subprocess
from src.agents import BaseAgent
from src.core.config import settings
class TerraformAgent(BaseAgent):
    def __init__(self): super().__init__('Terraform Agent')
    def plan(self):
        if settings.app_mode=='dry_run': return {'status':'dry_run','command':f'terraform -chdir={settings.terraform_working_dir} plan'}
        subprocess.run(['terraform',f'-chdir={settings.terraform_working_dir}','init'],capture_output=True,text=True)
        r=subprocess.run(['terraform',f'-chdir={settings.terraform_working_dir}','plan'],capture_output=True,text=True)
        return {'status':'success' if r.returncode==0 else 'failed','stdout':r.stdout[-1500:],'stderr':r.stderr[-1500:]}
    def execute(self, context=None): return {'terraform': self.plan()}
