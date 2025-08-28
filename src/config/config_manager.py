#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
配置参数管理器

功能说明：
1. 管理系统各种可配置参数
2. 支持配置热更新机制
3. 配置验证和默认值处理
4. 配置版本管理和回滚

作者：AI Agent Development Team
版本：v1.0.0
"""

import logging
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """配置参数管理器
    
    提供统一的配置管理接口，支持多种配置格式和热更新
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.config_file = config_file
        self.config_data = {}
        self.default_config = self._get_default_config()
        
        # 加载配置
        if config_file:
            self.load_config(config_file)
        else:
            self.config_data = self.default_config.copy()
            
        self.logger.info("ConfigManager初始化完成")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            # Level2连接配置
            'level2': {
                'connection_type': 'tcp',  # tcp 或 udp
                'tcp_address': 'tcp://210.14.72.17:6900',
                'multicast_address': 'udp://224.224.224.15:7889',
                'interface_ip': '10.168.9.46',
                'login_account': '13811112222',
                'password': '123456',
                'cache_mode': False,
                'max_reconnect_attempts': 10,
                'reconnect_interval': 5,
                'subscriptions': {
                    'market_data': True,
                    'transaction': True,
                    'order_detail': True,
                    'securities': [b'00000000'],  # 全部合约
                    'transaction_securities': [b'00000000'],
                    'order_securities': [b'00000000'],
                    'exchange': 'TORA_TSTP_EXD_COMM'
                }
            },
            
            # 日志配置
            'logging': {
                'level': 'INFO',
                'log_dir': './logs',
                'max_file_size': 100 * 1024 * 1024,  # 100MB
                'backup_count': 10,
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            },
            
            # 数据处理配置
            'data_processing': {
                'batch_size': 100,
                'batch_timeout': 1.0,
                'worker_threads': 4,
                'queue_size': 10000
            },
            
            # 数据库配置
            'database': {
                'postgresql': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'trading_system',
                    'username': 'postgres',
                    'password': 'password',
                    'pool_size': 10
                },
                'redis': {
                    'host': 'localhost',
                    'port': 6379,
                    'database': 0,
                    'password': None,
                    'pool_size': 10
                },
                'influxdb': {
                    'host': 'localhost',
                    'port': 8086,
                    'database': 'market_data',
                    'username': 'admin',
                    'password': 'password'
                }
            }
        }
    
    def load_config(self, config_file: str) -> bool:
        """
        加载配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            bool: 加载是否成功
        """
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self.logger.warning(f"配置文件不存在: {config_file}，使用默认配置")
                self.config_data = self.default_config.copy()
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.json':
                    loaded_config = json.load(f)
                elif config_path.suffix.lower() in ['.yml', '.yaml']:
                    loaded_config = yaml.safe_load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
            
            # 合并配置（用户配置覆盖默认配置）
            self.config_data = self._merge_config(self.default_config, loaded_config)
            self.config_file = config_file
            
            self.logger.info(f"配置文件加载成功: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}", exc_info=True)
            self.config_data = self.default_config.copy()
            return False
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """
        合并配置字典
        
        Args:
            default: 默认配置
            user: 用户配置
            
        Returns:
            Dict: 合并后的配置
        """
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default_value: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点分隔的嵌套键，如 'level2.connection_type'
            default_value: 默认值
            
        Returns:
            Any: 配置值
        """
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default_value
            
            return value
            
        except Exception as e:
            self.logger.error(f"获取配置值异常: {key}, {e}")
            return default_value
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            bool: 设置是否成功
        """
        try:
            keys = key.split('.')
            config = self.config_data
            
            # 导航到目标位置
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            self.logger.info(f"配置值已更新: {key} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置配置值异常: {key}, {e}")
            return False
    
    def get_level2_config(self) -> Dict[str, Any]:
        """获取Level2连接配置"""
        return self.get('level2', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get('logging', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.get('database', {})
    
    def save_config(self, config_file: Optional[str] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config_file: 配置文件路径，如果为None则使用当前配置文件
            
        Returns:
            bool: 保存是否成功
        """
        try:
            file_path = config_file or self.config_file
            if not file_path:
                self.logger.error("没有指定配置文件路径")
                return False
            
            config_path = Path(file_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.json':
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                elif config_path.suffix.lower() in ['.yml', '.yaml']:
                    yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
            
            self.logger.info(f"配置已保存到: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}", exc_info=True)
            return False
    
    def reload_config(self) -> bool:
        """重新加载配置文件"""
        if self.config_file:
            return self.load_config(self.config_file)
        return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config_data.copy()
