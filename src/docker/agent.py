import subprocess
from src.agents import BaseAgent
from src.core.config import settings
class DockerAgent(BaseAgent):
    def __init__(self): super().__init__('Docker Agent')
    def build(self):
        if settings.app_mode=='dry_run': return {'status':'dry_run','command':f'docker build -t {settings.docker_image_name} .'}
        r=subprocess.run(['docker','build','-t',settings.docker_image_name,'.'],capture_output=True,text=True)
        return {'status':'success' if r.returncode==0 else 'failed','stdout':r.stdout[-1000:],'stderr':r.stderr[-1000:]}
    def execute(self, context=None): return {'docker': self.build()}
