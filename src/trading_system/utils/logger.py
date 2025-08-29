"""
日志系统模块
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any


def setup_logger(config: Dict[str, Any]) -> logging.Logger:
    """设置日志系统
    
    Args:
        config: 日志配置字典
        
    Returns:
        配置好的logger实例
    """
    # 获取配置参数
    level = config.get('level', 'INFO')
    format_str = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_path = config.get('file_path', 'logs/trading_system.log')
    max_file_size = config.get('max_file_size', '100MB')
    backup_count = config.get('backup_count', 10)
    
    # 创建logger
    logger = logging.getLogger('trading_system')
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除已有的handlers
    logger.handlers.clear()
    
    # 创建formatter
    formatter = logging.Formatter(format_str)
    
    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件handler
    if file_path:
        # 确保日志目录存在
        log_file = Path(file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 解析文件大小
        size_bytes = _parse_size(max_file_size)
        
        # 创建RotatingFileHandler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=size_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def _parse_size(size_str: str) -> int:
    """解析文件大小字符串
    
    Args:
        size_str: 大小字符串，如 '100MB', '1GB'
        
    Returns:
        字节数
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # 默认为字节
        return int(size_str)


def get_logger(name: str = None) -> logging.Logger:
    """获取logger实例
    
    Args:
        name: logger名称，默认为trading_system
        
    Returns:
        logger实例
    """
    if name:
        return logging.getLogger(f'trading_system.{name}')
    else:
        return logging.getLogger('trading_system')
