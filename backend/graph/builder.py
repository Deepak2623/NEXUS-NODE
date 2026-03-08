"""LangGraph StateGraph assembly — builds and compiles the NEXUS-NODE mesh."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from graph.edges import route_after_execute, route_after_plan, route_after_verify
from graph.nodes.node_execute import node_execute
from graph.nodes.node_plan import node_plan
from graph.nodes.node_verify import node_verify
from graph.state import AgentState


def build_graph() -> StateGraph:  # type: ignore[type-arg]
    """Assemble and compile the NEXUS-NODE LangGraph cyclic state machine.

    Returns:
        Compiled LangGraph StateGraph (CompiledGraph).
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("node_plan", node_plan)
    graph.add_node("node_execute", node_execute)
    graph.add_node("node_verify", node_verify)

    # Entry point
    graph.set_entry_point("node_plan")

    # Conditional edges
    graph.add_conditional_edges(
        "node_plan",
        route_after_plan,
        {
            "node_execute": "node_execute",
            "node_verify": "node_verify",
            "END": END,
        },
    )

    graph.add_conditional_edges(
        "node_execute",
        route_after_execute,
        {
            "node_verify": "node_verify",
            "END": END,
        },
    )

    graph.add_conditional_edges(
        "node_verify",
        route_after_verify,
        {
            "node_plan": "node_plan",
            "END": END,
        },
    )

    return graph.compile()  # type: ignore[return-value]


# Module-level singleton — import this in the FastAPI app
nexus_graph = build_graph()
