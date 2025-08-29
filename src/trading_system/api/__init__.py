"""
API模块

提供RESTful API接口，包括数据查询、推荐获取和系统监控功能
"""

from .web_api import create_web_api, TradingSystemAPI

__all__ = [
    "create_web_api",
    "TradingSystemAPI"
]
