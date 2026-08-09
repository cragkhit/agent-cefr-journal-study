from datetime import datetime
from typing import Literal

import pytest

from api.routers.mcp._mcp_models import AgentResponse
from api.routers.mcp._utils.agent_sorting import sort_agents


def create_test_agent(
    agent_id: str,
    run_count: int = 0,
    total_cost_usd: float = 0.0,
    last_active_ats: list[str | None] | None = None,
) -> AgentResponse:
    """Helper function to create test agents."""
    if last_active_ats is None:
        last_active_ats = [None]

    schemas = [
        AgentResponse.AgentSchema(
            agent_schema_id=i + 1,
            created_at=datetime(2024, 1, 1).isoformat(),
            input_json_schema={},
            output_json_schema={},
            is_hidden=False,
            last_active_at=last_active_at,
        )
        for i, last_active_at in enumerate(last_active_ats)
    ]

    return AgentResponse(
        agent_id=agent_id,
        is_public=True,
        schemas=schemas,
        run_count=run_count,
        total_cost_usd=total_cost_usd,
    )


class TestSortAgents:
    """Test suite for agent sorting functionality."""

    def test_sort_by_last_active_first_basic(self):
        """Test sorting by latest active first with basic scenarios."""
        agents = [
            create_test_agent("agent1", last_active_ats=["2024-01-01T00:00:00"]),
            create_test_agent("agent2", last_active_ats=["2024-01-03T00:00:00"]),
            create_test_agent("agent3", last_active_ats=["2024-01-02T00:00:00"]),
        ]

        sorted_agents = sort_agents(agents, "last_active_first")

        assert [a.agent_id for a in sorted_agents] == ["agent2", "agent3", "agent1"]

    def test_sort_by_last_active_first_multiple_schemas(self):
        """Test sorting by latest active first with multiple schemas per agent."""
        agents = [
            create_test_agent(
                "agent1",
                last_active_ats=["2024-01-01T00:00:00", "2024-01-05T00:00:00", "2024-01-02T00:00:00"],
            ),
            create_test_agent(
                "agent2",
                last_active_ats=["2024-01-03T00:00:00", "2024-01-04T00:00:00"],
            ),
            create_test_agent(
                "agent3",
                last_active_ats=["2024-01-06T00:00:00", "2024-01-01T00:00:00"],
            ),
        ]

        sorted_agents = sort_agents(agents, "last_active_first")

        # agent3 has max date 2024-01-06, agent1 has max date 2024-01-05, agent2 has max date 2024-01-04
        assert [a.agent_id for a in sorted_agents] == ["agent3", "agent1", "agent2"]

    def test_sort_by_last_active_first_with_none_values(self):
        """Test sorting when some agents have no active dates."""
        agents = [
            create_test_agent("agent1", last_active_ats=[None, None]),
            create_test_agent("agent2", last_active_ats=["2024-01-03T00:00:00"]),
            create_test_agent("agent3", last_active_ats=[None]),
            create_test_agent("agent4", last_active_ats=["2024-01-01T00:00:00", None]),
        ]

        sorted_agents = sort_agents(agents, "last_active_first")

        # Agents with dates come first (sorted by date desc), then agents without dates (sorted by agent_id desc due to reverse=True)
        assert [a.agent_id for a in sorted_agents] == ["agent2", "agent4", "agent3", "agent1"]

    def test_sort_by_last_active_first_stable_ordering(self):
        """Test that sorting is stable for agents with same/no dates."""
        # All agents have no active dates
        agents = [
            create_test_agent("zebra", last_active_ats=[None]),
            create_test_agent("alpha", last_active_ats=[None]),
            create_test_agent("beta", last_active_ats=[None]),
        ]

        sorted_agents = sort_agents(agents, "last_active_first")

        # Should be sorted by agent_id when all have no dates
        assert [a.agent_id for a in sorted_agents] == ["zebra", "beta", "alpha"]

    def test_sort_by_most_costly_first(self):
        """Test sorting by cost."""
        agents = [
            create_test_agent("agent1", total_cost_usd=10.5),
            create_test_agent("agent2", total_cost_usd=100.0),
            create_test_agent("agent3", total_cost_usd=50.25),
            create_test_agent("agent4", total_cost_usd=100.0),  # Same cost as agent2
        ]

        sorted_agents = sort_agents(agents, "most_costly_first")

        # agent2 and agent4 have same cost, so they're sorted by agent_id
        assert [a.agent_id for a in sorted_agents] == ["agent4", "agent2", "agent3", "agent1"]

    def test_sort_by_most_runs_first(self):
        """Test sorting by run count."""
        agents = [
            create_test_agent("agent1", run_count=5),
            create_test_agent("agent2", run_count=100),
            create_test_agent("agent3", run_count=50),
            create_test_agent("agent4", run_count=100),  # Same count as agent2
        ]

        sorted_agents = sort_agents(agents, "most_runs_first")

        # agent2 and agent4 have same count, so they're sorted by agent_id
        assert [a.agent_id for a in sorted_agents] == ["agent4", "agent2", "agent3", "agent1"]

    def test_sort_by_most_costly_first_all_zero(self):
        """Test cost sorting when all agents have zero cost."""
        agents = [
            create_test_agent("zebra", total_cost_usd=0.0),
            create_test_agent("alpha", total_cost_usd=0.0),
            create_test_agent("beta", total_cost_usd=0.0),
        ]

        sorted_agents = sort_agents(agents, "most_costly_first")

        # Should be sorted by agent_id when all have same cost
        assert [a.agent_id for a in sorted_agents] == ["zebra", "beta", "alpha"]

    def test_sort_by_most_runs_first_all_zero(self):
        """Test run count sorting when all agents have zero runs."""
        agents = [
            create_test_agent("zebra", run_count=0),
            create_test_agent("alpha", run_count=0),
            create_test_agent("beta", run_count=0),
        ]

        sorted_agents = sort_agents(agents, "most_runs_first")

        # Should be sorted by agent_id when all have same run count
        assert [a.agent_id for a in sorted_agents] == ["zebra", "beta", "alpha"]

    def test_empty_list(self):
        """Test sorting an empty list."""
        agents: list[AgentResponse] = []

        sorted_agents = sort_agents(agents, "last_active_first")
        assert sorted_agents == []

        sorted_agents = sort_agents(agents, "most_costly_first")
        assert sorted_agents == []

        sorted_agents = sort_agents(agents, "most_runs_first")
        assert sorted_agents == []

    def test_single_agent(self):
        """Test sorting a single agent."""
        agents = [create_test_agent("agent1")]

        sorted_agents = sort_agents(agents, "last_active_first")
        assert [a.agent_id for a in sorted_agents] == ["agent1"]

        sorted_agents = sort_agents(agents, "most_costly_first")
        assert [a.agent_id for a in sorted_agents] == ["agent1"]

        sorted_agents = sort_agents(agents, "most_runs_first")
        assert [a.agent_id for a in sorted_agents] == ["agent1"]

    def test_sort_modifies_in_place(self):
        """Test that sort_agents modifies the list in place."""
        agents = [
            create_test_agent("agent1", run_count=5),
            create_test_agent("agent2", run_count=10),
        ]

        original_list = agents
        sorted_agents = sort_agents(agents, "most_runs_first")

        # Should return the same list object
        assert sorted_agents is original_list
        assert [a.agent_id for a in agents] == ["agent2", "agent1"]

    @pytest.mark.parametrize("sort_by", ["last_active_first", "most_costly_first", "most_runs_first"])
    def test_sort_preserves_agent_data(
        self,
        sort_by: Literal["last_active_first", "most_costly_first", "most_runs_first"],
    ):
        """Test that sorting doesn't modify agent data."""
        agent = create_test_agent(
            "test_agent",
            run_count=10,
            total_cost_usd=100.0,
            last_active_ats=["2024-01-01T00:00:00"],
        )
        agents = [agent]

        sort_agents(agents, sort_by)

        # Verify agent data is unchanged
        assert agents[0].agent_id == "test_agent"
        assert agents[0].run_count == 10
        assert agents[0].total_cost_usd == 100.0
        assert agents[0].schemas[0].last_active_at == "2024-01-01T00:00:00"
