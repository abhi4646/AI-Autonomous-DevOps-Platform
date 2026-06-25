class BaseAgent:
    def __init__(self, name): self.name=name
    def execute(self, context=None): raise NotImplementedError
