import autogen
from typing import List, Dict, Any
from functions import retrieve_stock_data, plot_stock_comparison, analyze_market_data

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["gpt-4"]}
)

financial_tasks = [
    "What are the current stock prices of NVDA and TSLA, and how is their performance over the past month?",
    "Investigate possible reasons for the stock performance patterns we're seeing.",
    "Create a visualization comparing these stocks over the past month.",
    "Generate a comprehensive market analysis report using all gathered information."
]

financial_assistant = autogen.AssistantAgent(
    name="financial_assistant",
    llm_config={"config_list": config_list},
    system_message="You are a financial analysis expert. Help analyze stock data and generate insights."
)

research_assistant = autogen.AssistantAgent(
    name="research_assistant",
    llm_config={"config_list": config_list},
    system_message="You are a market research specialist. Investigate and explain market trends and company performance."
)

report_writer = autogen.AssistantAgent(
    name="report_writer",
    llm_config={"config_list": config_list},
    system_message="You are a professional writer. Transform financial analysis into engaging reports. Reply TERMINATE when done."
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
    return await user_proxy.a_initiate_chats(

if __name__ == "__main__":
    import asyncio
    chat_results = asyncio.run(main(
        [
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
        ]
    ))
