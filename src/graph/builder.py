from langgraph.graph import StateGraph, END
from src.graph.state import ResearchState
from src.graph.nodes.planner import planner_node
from src.graph.nodes.search import search_node
from src.graph.nodes.verifier import verifier_node
from src.graph.nodes.reflector import reflector_node
from src.graph.nodes.synthesizer import synthesizer_node


def route_after_verifier(state: ResearchState):
    if state.get("needs_retry", False):
        return "reflector"
    return "synthesizer"


def build_research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("reflector", reflector_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "search")
    graph.add_edge("search", "verifier")

    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {
            "reflector": "reflector",
            "synthesizer": "synthesizer",
        },
    )

    graph.add_edge("reflector", "search")
    graph.add_edge("synthesizer", END)

    return graph.compile()
