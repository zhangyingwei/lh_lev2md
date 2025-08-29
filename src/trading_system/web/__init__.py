"""
Web前端模块

提供简洁的Web前端界面，展示实时数据、推荐结果和系统状态
"""

from .static_server import create_static_server

__all__ = [
    "create_static_server"
]
