import autogen
from typing import List, Dict, Any

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["gpt-4"]}
)

financial_tasks = [
    "Analyze the current stock prices and performance metrics provided.",
    "Based on the volatility and volume data provided, investigate possible reasons for the performance patterns.",
    "Review and explain insights from the stock comparison visualization.",
    "Generate a comprehensive market analysis report incorporating all data and insights."
]

financial_assistant = autogen.AssistantAgent(
    name="financial_assistant",
    llm_config={"config_list": config_list},
    system_message="""You are a financial analysis expert. Help analyze stock data and generate insights.
    You have access to real-time stock data including:
    - Current prices and percentage changes
    - Trading volume statistics
    - Volatility metrics
    - Price comparison visualizations
    Use this data to provide detailed market analysis."""
)

research_assistant = autogen.AssistantAgent(
    name="research_assistant",
    llm_config={"config_list": config_list},
    system_message="""You are a market research specialist. Investigate and explain market trends and company performance.
    You have access to detailed market metrics including:
    - Stock volatility data
    - Trading volume patterns
    - Price movement analysis
    Use this information to explain market behavior and company performance."""
)

report_writer = autogen.AssistantAgent(
    name="report_writer",
    llm_config={"config_list": config_list},
    system_message="""You are a professional writer. Transform financial analysis into engaging reports.
    Your report should incorporate:
    - Current stock prices and performance metrics
    - Volume and volatility analysis
    - Visual comparisons and their interpretations
    - Market trend explanations
    Create a comprehensive yet accessible report. Reply TERMINATE when done."""
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={
        "work_dir": "workspace",
        "use_docker": False,
    }
)

async def main():
    
    return await user_proxy.a_initiate_chats([
        {
            "chat_id": 1,
            "recipient": financial_assistant,
            "message": financial_tasks[0],
            "summary_method": "reflection_with_llm",
        },
        {
            "chat_id": 2,
            "prerequisites": [1],
            "recipient": research_assistant,
            "message": financial_tasks[1],
            "summary_method": "reflection_with_llm",
        },
        {
            "chat_id": 3,
            "prerequisites": [1],
            "recipient": financial_assistant,
            "message": financial_tasks[2],
            "summary_method": "reflection_with_llm",
        },
        {
            "chat_id": 4,
            "prerequisites": [1, 2, 3],
            "recipient": report_writer,
            "message": financial_tasks[3],
        }
    ])

if __name__ == "__main__":
    import asyncio
    chat_results = asyncio.run(main())
