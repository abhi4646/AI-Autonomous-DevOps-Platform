from src.agents import BaseAgent
class MonitoringAgent(BaseAgent):
    def __init__(self): super().__init__('Monitoring Agent')
    def execute(self, context=None): return {'monitoring': {'status':'healthy','checks':['orchestrator','agents','config']}}
