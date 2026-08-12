from typing import List, TypeVar, Any

from goat.classes.tool_base import zon_to_pydantic
from langchain.tools import Tool
from langchain_core.tools import BaseTool
from goat import ToolBase, WalletClientBase, get_tools


def get_on_chain_tools(wallet: WalletClientBase, plugins: List[Any]) -> List[BaseTool]:
    """Create LangChain tools from GOAT tools.

    Args:
        wallet: A wallet client instance
        plugins: List of plugin instances

    Returns:
        List of LangChain Tool instances configured with the GOAT tools
    """
    tools: List[ToolBase] = get_tools(wallet=wallet, plugins=plugins)

    langchain_tools = []
    for t in tools:
        # Create a LangChain Tool for each GOAT tool
        tool = Tool(
            name=t.name,
            description=t.description,
            func=lambda args, t=t: t.execute(args),
            args_schema=zon_to_pydantic(t.parameters),
        )
        langchain_tools.append(tool)

    return langchain_tools
