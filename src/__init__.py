# 股票自动交易系统
# Stock Automatic Trading System
# 
# 基于AI Agent开发方法论的股票自动交易系统
# 支持Level2实时行情数据处理、历史评分算法、股票池策略等功能
#
# 版本: v1.0.0
# 作者: AI Agent Development Team

__version__ = "1.0.0"
__author__ = "AI Agent Development Team"
__description__ = "股票自动交易系统 - Stock Automatic Trading System"

# 导入核心模块
from .data_processing import MarketDataReceiver, DataHandler
from .config import ConfigManager
from .logging import LogManager

__all__ = [
    'MarketDataReceiver',
    'DataHandler', 
    'ConfigManager',
    'LogManager'
]
