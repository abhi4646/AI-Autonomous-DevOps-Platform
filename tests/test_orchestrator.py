from src.orchestrator.orchestrator import Orchestrator
from src.monitoring.agent import MonitoringAgent

def test_orchestrator_runs_agent():
    o=Orchestrator(); o.register_agent(MonitoringAgent()); r=o.run(); assert 'Monitoring Agent' in r
