"""
配置管理器模块
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = {}
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                # 如果配置文件不存在，使用默认配置
                self.config = self._get_default_config()
                self.save_config()
            
            return self.config
            
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            self.config = self._get_default_config()
            return self.config
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            return True
            
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项
        
        Args:
            key: 配置键，支持点分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """设置配置项
        
        Args:
            key: 配置键，支持点分隔的嵌套键
            value: 配置值
            save: 是否立即保存到文件
            
        Returns:
            是否设置成功
        """
        try:
            keys = key.split('.')
            target = self.config
            
            # 导航到目标位置
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            
            # 设置值
            target[keys[-1]] = value
            
            # 保存到文件
            if save:
                return self.save_config()
            
            return True
            
        except Exception as e:
            logging.error(f"设置配置项失败: {e}")
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'system': {
                'name': '股票自动交易系统',
                'version': '1.0.0',
                'environment': 'development',
                'timezone': 'Asia/Shanghai'
            },
            'database': {
                'sqlite': {
                    'path': 'data/trading_system.db',
                    'echo': False
                },
                'redis': {
                    'host': 'localhost',
                    'port': 6379,
                    'db': 0,
                    'password': None
                }
            },
            'level2': {
                'connection_mode': 'tcp',
                'tcp_address': 'tcp://127.0.0.1:6900',
                'user_id': '',
                'password': '',
                'max_reconnect_attempts': 10,
                'reconnect_interval': 5
            },
            'scoring_parameters': {
                'x1_percent': 0.05,
                'x2_percent': 0.03,
                'x3_percent': 0.04,
                'decline_threshold': -0.02,
                'limit_up_seal_threshold': 30000000,
                'reseal_count_threshold': 5
            },
            'pool_parameters': {
                'pool_a_min_market_value': 10,
                'pool_a_max_market_value': 100,
                'pool_b_min_market_value': 50,
                'pool_b_max_market_value': 400,
                'min_auction_amount': 10000000,
                'min_opening_turnover': 0.002,
                'min_auction_change': -0.02,
                'min_auction_ratio': 0.1
            },
            'strategy_parameters': {
                'main_fund_threshold_1': 10000000,
                'main_fund_ratio_1': 0.005,
                'change_threshold_1': 0.01,
                'buy_ratio_1': 0.0005,
                'main_fund_threshold_2': 100000000,
                'main_fund_ratio_2': 0.005,
                'change_threshold_2': 0.07,
                'amount_threshold': 300000000,
                'turnover_threshold': 0.01
            },
            'risk_management': {
                'total_capital': 1000000,
                'max_position_ratio': 0.1,
                'max_daily_loss': 0.05,
                'stop_loss_ratio': 0.08,
                'take_profit_ratio': 0.15
            },
            'performance': {
                'max_workers': 4,
                'queue_size': 10000,
                'batch_size': 100,
                'process_interval': 0.01,
                'large_order_threshold': 200000,
                'super_large_threshold': 1000000
            },
            'monitoring': {
                'enabled': True,
                'metrics_interval': 30,
                'alert_thresholds': {
                    'cpu_usage': 80.0,
                    'memory_usage': 85.0,
                    'disk_usage': 90.0,
                    'queue_size': 5000,
                    'processing_latency': 1.0
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_path': 'logs/trading_system.log',
                'max_file_size': '100MB',
                'backup_count': 10,
                'rotation': 'daily'
            }
        }
