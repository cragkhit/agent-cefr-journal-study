from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, Memory
from app.agent.toolcall import ToolCallAgent


class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act()


class ReactAgent(ToolCallAgent):
    """
    A React agent that can use tools.
    
    This class extends ToolCallAgent to provide tool handling capabilities
    while maintaining compatibility with code that expects a ReactAgent.
    """
    
    name: str = "react"
    description: str = "an agent that implements the ReAct paradigm with tool handling capabilities."
    
    # Inherit system_prompt, next_step_prompt, and other attributes from ToolCallAgent
