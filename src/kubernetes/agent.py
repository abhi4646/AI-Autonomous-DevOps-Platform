import subprocess
from src.agents import BaseAgent
from src.core.config import settings
class KubernetesAgent(BaseAgent):
    def __init__(self): super().__init__('Kubernetes Agent')
    def get_pods(self):
        if settings.app_mode=='dry_run': return {'status':'dry_run','command':f'kubectl get pods -n {settings.kubernetes_namespace}'}
        cmd=['kubectl'] + (['--kubeconfig',settings.kubeconfig_path] if settings.kubeconfig_path else []) + ['get','pods','-n',settings.kubernetes_namespace]
        r=subprocess.run(cmd,capture_output=True,text=True); return {'status':'success' if r.returncode==0 else 'failed','stdout':r.stdout,'stderr':r.stderr}
    def execute(self, context=None): return {'kubernetes': self.get_pods()}
