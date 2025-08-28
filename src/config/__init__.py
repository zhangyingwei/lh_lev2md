# 配置管理模块
# Configuration Management Module
#
# 负责系统各种可配置参数的管理
# 支持配置热更新、配置验证、默认值处理等功能

from .config_manager import ConfigManager

__all__ = [
    'ConfigManager'
]
