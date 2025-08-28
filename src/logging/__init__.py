# 日志管理模块
# Logging Management Module
#
# 提供统一的日志管理接口
# 支持结构化日志、日志轮转、日志聚合等功能

from .log_manager import LogManager

__all__ = [
    'LogManager'
]
