"""Agent sorting utilities for MCP service."""

from api.routers.mcp._mcp_models import AgentResponse, SortAgentBy


def sort_agents(
    agents: list[AgentResponse],
    sort_by: SortAgentBy,
) -> list[AgentResponse]:
    """Sort agents based on the specified criteria with stable secondary sorting by agent_id.

    Args:
        agents: List of agent responses to sort
        sort_by: Sort criteria
            - "last_active_first": Sort by maximum last_active_at across all schemas
            - "most_costly_first": Sort by total_cost_usd
            - "most_runs_first": Sort by run_count

    Returns:
        Sorted list of agents (modifies in place and returns the list)
    """
    if sort_by == "last_active_first":

        def get_max_last_active_at(agent: AgentResponse) -> tuple[str, str]:
            """Get the maximum last_active_at across all schemas, handling None values.
            Returns a tuple of (max_last_active_at, agent_id) for stable sorting."""
            active_dates = [schema.last_active_at for schema in agent.schemas if schema.last_active_at is not None]
            if not active_dates:
                # Use a very old date for agents with no active dates, ensuring they sort last
                # Using "0000" as a prefix ensures these sort after all real dates (which start with "2")
                max_date = "0000-00-00T00:00:00"
            else:
                max_date = max(active_dates)

            # Return tuple with agent_id as secondary sort key for stable ordering
            return (max_date, agent.agent_id)

        agents.sort(key=get_max_last_active_at, reverse=True)
    elif sort_by == "most_costly_first":
        agents.sort(key=lambda x: (x.total_cost_usd, x.agent_id), reverse=True)
    elif sort_by == "most_runs_first":
        agents.sort(key=lambda x: (x.run_count, x.agent_id), reverse=True)

    return agents
