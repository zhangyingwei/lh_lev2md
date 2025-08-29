"""
服务层模块

提供系统集成服务、API服务和业务逻辑封装
"""

from .trading_service import TradingSystemService, create_trading_service

__all__ = [
    "TradingSystemService",
    "create_trading_service"
]
