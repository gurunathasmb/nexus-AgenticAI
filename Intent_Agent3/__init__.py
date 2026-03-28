from Intent_Agent3.registry import dispatcher
from Intent_Agent3.llm_agent import LLMAgent
from Intent_Agent3.student_agent import StudentAgent
from Intent_Agent3.router_agent import RouterAgent
from Intent_Agent3.intent_agent import HierarchicalIntentAgent
from table_agent.agent import TableAgent


def init_agents():
    """Register all agents with the dispatcher."""
    dispatcher.register(LLMAgent())
    dispatcher.register(StudentAgent())
    dispatcher.register(TableAgent())
    dispatcher.register(HierarchicalIntentAgent())
    dispatcher.register(RouterAgent())
