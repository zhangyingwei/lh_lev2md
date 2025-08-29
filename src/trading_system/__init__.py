"""
股票自动交易系统

基于Level2行情的股票自动交易系统，支持历史评分计算、股票池筛选和实时买入策略。
"""

__version__ = "1.0.0"
__author__ = "AI Agent"
__email__ = "ai@trading-system.com"

# 导出主要类和函数
from .main import TradingSystem

__all__ = [
    "TradingSystem",
    "__version__",
]
