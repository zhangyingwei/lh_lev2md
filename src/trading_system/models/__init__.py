"""
数据模型模块
"""

from .base import BaseModel, DatabaseManager, db_manager
from .stock_data import (
    StockInfo,
    DailyQuote,
    Level2Snapshot,
    Level2Transaction,
    Level2OrderDetail
)
from .scoring_data import (
    HistoricalScore,
    StockPoolResult,
    TradingSignal,
    SystemMetrics
)
from .data_lifecycle import DataLifecycleManager

__all__ = [
    # 基础类
    "BaseModel",
    "DatabaseManager",
    "db_manager",

    # 股票数据模型
    "StockInfo",
    "DailyQuote",
    "Level2Snapshot",
    "Level2Transaction",
    "Level2OrderDetail",

    # 评分数据模型
    "HistoricalScore",
    "StockPoolResult",
    "TradingSignal",
    "SystemMetrics",

    # 数据生命周期管理
    "DataLifecycleManager"
]
