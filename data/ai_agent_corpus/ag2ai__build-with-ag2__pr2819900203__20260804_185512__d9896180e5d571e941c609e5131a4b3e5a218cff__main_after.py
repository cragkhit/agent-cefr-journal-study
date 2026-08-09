import autogen
from typing import List, Dict, Any
from functions import retrieve_stock_data, plot_stock_comparison, analyze_market_data

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

async def analyze_stocks():
    """Run stock analysis using local functions before initiating agent chat."""
    # Get current stock data
    nvda_price, nvda_change = retrieve_stock_data("NVDA", days=30)
    tsla_price, tsla_change = retrieve_stock_data("TSLA", days=30)
    
    # Create comparison visualization
    plot_file = plot_stock_comparison(["NVDA", "TSLA"], days=30)
    
    # Get detailed market analysis
    nvda_analysis = analyze_market_data("NVDA", days=30)
    tsla_analysis = analyze_market_data("TSLA", days=30)
    
    return {
        "NVDA": {"price": nvda_price, "change": nvda_change, **nvda_analysis},
        "TSLA": {"price": tsla_price, "change": tsla_change, **tsla_analysis},
        "plot": plot_file
    }

async def main():
    # Run stock analysis first
    analysis_results = await analyze_stocks()
    
    # Update first task with actual data
    financial_tasks[0] = (
        f"NVDA current price: ${analysis_results['NVDA']['price']:.2f} "
        f"(change: {analysis_results['NVDA']['change']:.1f}%), "
        f"TSLA current price: ${analysis_results['TSLA']['price']:.2f} "
        f"(change: {analysis_results['TSLA']['change']:.1f}%). "
        "What insights can you provide about their performance?"
    )
    
    # Update task messages with actual data
    task_messages = [
        f"{financial_tasks[0]}\nData:\n" + \
        f"NVDA: Price=${analysis_results['NVDA']['price']:.2f}, Change={analysis_results['NVDA']['change']:.1f}%, " + \
        f"Avg Volume={analysis_results['NVDA']['avg_volume']:.0f}, Volatility={analysis_results['NVDA']['volatility']:.1f}%\n" + \
        f"TSLA: Price=${analysis_results['TSLA']['price']:.2f}, Change={analysis_results['TSLA']['change']:.1f}%, " + \
        f"Avg Volume={analysis_results['TSLA']['avg_volume']:.0f}, Volatility={analysis_results['TSLA']['volatility']:.1f}%",
        
        f"{financial_tasks[1]}\nMetrics:\n" + \
        f"NVDA Volatility: {analysis_results['NVDA']['volatility']:.1f}%, Volume: {analysis_results['NVDA']['avg_volume']:.0f}\n" + \
        f"TSLA Volatility: {analysis_results['TSLA']['volatility']:.1f}%, Volume: {analysis_results['TSLA']['avg_volume']:.0f}",
        
        f"{financial_tasks[2]}\nVisualization saved as: {analysis_results['plot']}\n" + \
        f"Price ranges:\nNVDA: ${analysis_results['NVDA']['low']:.2f} - ${analysis_results['NVDA']['high']:.2f}\n" + \
        f"TSLA: ${analysis_results['TSLA']['low']:.2f} - ${analysis_results['TSLA']['high']:.2f}",
        
        f"{financial_tasks[3]}\nPlease incorporate all the data and visualizations provided in the previous messages."
    ]
    
    return await user_proxy.a_initiate_chats([
        {
            "chat_id": 1,
            "recipient": financial_assistant,
            "message": task_messages[0],
            "summary_method": "reflection_with_llm",
        },
        {
            "chat_id": 2,
            "prerequisites": [1],
            "recipient": research_assistant,
            "message": task_messages[1],
            "summary_method": "reflection_with_llm",
        },
        {
            "chat_id": 3,
            "prerequisites": [1],
            "recipient": financial_assistant,
            "message": task_messages[2],
            "summary_method": "reflection_with_llm",
        },
        {
            "chat_id": 4,
            "prerequisites": [1, 2, 3],
            "recipient": report_writer,
            "message": task_messages[3],
        }
    ])

if __name__ == "__main__":
    import asyncio
    chat_results = asyncio.run(main())
