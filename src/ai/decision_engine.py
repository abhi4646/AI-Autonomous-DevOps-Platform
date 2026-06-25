class DecisionEngine:
    def decide_agents(self, ticket):
        text=f"{ticket.get('summary','')} {ticket.get('description','')}".lower(); agents=[]
        for key, words in {'github':['repo','branch','pull request','code','github'],'docker':['docker','container','image'],'terraform':['terraform','infrastructure','cloud'],'kubernetes':['kubernetes','k8s','pod','deployment'],'ansible':['ansible','server','configure']}.items():
            if any(w in text for w in words): agents.append(key)
        return {'recommended_agents': agents or ['github','monitoring']}
