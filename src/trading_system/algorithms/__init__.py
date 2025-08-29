"""
算法模块

包含涨停炸板评分算法、股票筛选机制和实时计算引擎
"""

from .limit_up_break_analyzer import (
    LimitUpBreakAnalyzer,
    LimitUpBreakDetector,
    LimitUpBreakScorer,
    LimitUpBreakEvent,
    create_limit_up_analyzer
)
from .stock_filter import (
    StockFilter,
    StockSorter,
    StockRecommendationEngine,
    StockFilterManager,
    StockRecommendation,
    FilterCondition,
    SortCondition,
    FilterOperator,
    SortOrder,
    create_stock_filter_manager
)
from .realtime_engine import (
    RealtimeComputeEngine,
    IncrementalCache,
    ComputeTask,
    ComputeResult,
    EngineStats,
    create_realtime_engine
)

__all__ = [
    "LimitUpBreakAnalyzer",
    "LimitUpBreakDetector",
    "LimitUpBreakScorer",
    "LimitUpBreakEvent",
    "create_limit_up_analyzer",
    "StockFilter",
    "StockSorter",
    "StockRecommendationEngine",
    "StockFilterManager",
    "StockRecommendation",
    "FilterCondition",
    "SortCondition",
    "FilterOperator",
    "SortOrder",
    "create_stock_filter_manager",
    "RealtimeComputeEngine",
    "IncrementalCache",
    "ComputeTask",
    "ComputeResult",
    "EngineStats",
    "create_realtime_engine"
]
