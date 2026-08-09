#!/usr/bin/env python3

"""
Test script to check the correct import name for OpenAI Agents SDK.
"""

try:
    import agents
    print("Successfully imported as 'openai_agents'")
except ImportError:
    print("Failed to import as 'openai_agents'")

try:
    import agents
    print("Successfully imported as 'openai.agents'")
except ImportError:
    print("Failed to import as 'openai.agents'")

try:
    import agents.agent
    print("Successfully imported as 'openai_agents.agent'")
except ImportError:
    print("Failed to import as 'openai_agents.agent'")

try:
    import agents.agent
    print("Successfully imported as 'openai.agents.agent'")
except ImportError:
    print("Failed to import as 'openai.agents.agent'")
