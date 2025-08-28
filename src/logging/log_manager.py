#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
日志管理器

功能说明：
1. 统一日志管理接口
2. 支持结构化日志格式
3. 日志轮转和压缩
4. 多级别日志处理

作者：AI Agent Development Team
版本：v1.0.0
"""

import logging
import logging.handlers
import json
import os
from typing import Dict, Any
from datetime import datetime
from pathlib import Path


class LogManager:
    """统一日志管理器
    
    提供结构化日志记录、日志轮转等功能
    """
    
    def __init__(self, config: Dict):
        """
        初始化日志管理器
        
        Args:
            config: 日志配置参数
        """
        self.config = config
        self.loggers = {}
        self.handlers = {}
        self.formatters = {}
        
        # 创建日志目录
        self.log_dir = Path(config.get('log_dir', './logs'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志系统
        self._setup_formatters()
        self._setup_handlers()
        self._setup_loggers()
    
    def _setup_formatters(self):
        """设置日志格式器"""
        
        # JSON格式器 - 用于结构化日志
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno,
                    'message': record.getMessage(),
                    'thread_id': record.thread,
                    'thread_name': record.threadName,
                    'process_id': record.process
                }
                
                # 添加异常信息
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        # 标准格式器 - 用于控制台输出
        standard_format = self.config.get(
            'format',
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        self.formatters = {
            'json': JsonFormatter(),
            'standard': logging.Formatter(standard_format)
        }
    
    def _setup_handlers(self):
        """设置日志处理器"""
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.formatters['standard'])
        self.handlers['console'] = console_handler
        
        # 应用日志文件处理器
        app_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / 'application.log',
            maxBytes=self.config.get('max_file_size', 100 * 1024 * 1024),  # 100MB
            backupCount=self.config.get('backup_count', 10),
            encoding='utf-8'
        )
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(self.formatters['json'])
        self.handlers['application'] = app_handler
        
        # 错误日志文件处理器
        error_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / 'error.log',
            maxBytes=self.config.get('max_file_size', 50 * 1024 * 1024),  # 50MB
            backupCount=self.config.get('backup_count', 20),
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.formatters['json'])
        self.handlers['error'] = error_handler
        
        # 数据流日志处理器
        data_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / 'dataflow.log',
            maxBytes=self.config.get('max_file_size', 200 * 1024 * 1024),  # 200MB
            backupCount=self.config.get('backup_count', 5),
            encoding='utf-8'
        )
        data_handler.setLevel(logging.DEBUG)
        data_handler.setFormatter(self.formatters['json'])
        self.handlers['dataflow'] = data_handler
    
    def _setup_loggers(self):
        """设置日志记录器"""
        
        # 根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 应用日志记录器
        app_logger = logging.getLogger('trading_system')
        app_logger.setLevel(logging.DEBUG)
        app_logger.addHandler(self.handlers['console'])
        app_logger.addHandler(self.handlers['application'])
        app_logger.addHandler(self.handlers['error'])
        app_logger.propagate = False
        self.loggers['application'] = app_logger
        
        # 数据流日志记录器
        data_logger = logging.getLogger('trading_system.dataflow')
        data_logger.setLevel(logging.DEBUG)
        data_logger.addHandler(self.handlers['dataflow'])
        data_logger.propagate = False
        self.loggers['dataflow'] = data_logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        return logging.getLogger(name)
    
    def setup_module_logger(self, module_name: str) -> logging.Logger:
        """为模块设置日志记录器"""
        logger = logging.getLogger(f"trading_system.{module_name}")
        logger.setLevel(logging.DEBUG)
        
        # 添加处理器
        if 'console' in self.handlers:
            logger.addHandler(self.handlers['console'])
        if 'application' in self.handlers:
            logger.addHandler(self.handlers['application'])
        if 'error' in self.handlers:
            logger.addHandler(self.handlers['error'])
        
        logger.propagate = False
        return logger
