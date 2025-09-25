from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from web.utils.mongodb_report_manager import MongoDBReportManager

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('default')

stock_code = "600988"
report_date = "2025-09-22"
analysts = ["market", "social", "news", "fundamentals"]

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"  # Use a different model
config["backend_url"] = "https://api.deepseek.com"  # Use a different backend
config["deep_think_llm"] = "deepseek-chat"  # Use a different model
config["quick_think_llm"] = "deepseek-chat"  # Use a different model
config["max_debate_rounds"] = 1  # Increase debate rounds
config["online_tools"] = True  # Increase debate rounds

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
final_state, decision = ta.propagate(stock_code, "2025-09-22")
# ['messages', 'company_of_interest', 'trade_date', 'sender', 'market_report', 'sentiment_report', 'news_report', 'fundamentals_report', 'investment_debate_state', 'investment_plan', 'trader_investment_plan', 'risk_debate_state', 'final_trade_decision']

analysis_results = {"summary": "",
                    "analysts": analysts,
                    "research_depth": 1}
messages = final_state.pop("messages", None)

"""显示报告详细信息（调试用）"""
mongodb_manager = MongoDBReportManager()
if mongodb_manager.connected:
    result = mongodb_manager.save_analysis_report(stock_code, analysis_results, final_state)

# print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
