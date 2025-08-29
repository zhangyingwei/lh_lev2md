"""
Level2数据接收器测试脚本

用于测试Level2数据接收器的基本功能，包括连接、登录、订阅和数据接收
"""

import sys
import time
import asyncio
from typing import Dict, Any

from ..config import ConfigManager
from ..models.database_init import initialize_database
from .level2_receiver import create_level2_receiver
from ..utils.logger import setup_logger


class Level2ReceiverTester:
    """Level2数据接收器测试类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化测试器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # 设置日志
        self.logger = setup_logger(self.config.get("logging", {}))
        
        # 初始化数据库
        db_config = self.config.get('database', {}).get('sqlite', {})
        db_url = f"sqlite:///{db_config.get('path', 'data/trading_system.db')}"
        initialize_database(db_url)
        
        # 创建Level2接收器
        level2_config = self.config.get('level2', {})
        self.receiver = create_level2_receiver(level2_config)
        
        # 数据统计
        self.data_count = {
            'market_data': 0,
            'transaction': 0,
            'order_detail': 0
        }
        
        # 注册数据回调
        self._register_callbacks()
    
    def _register_callbacks(self):
        """注册数据处理回调函数"""
        
        def on_market_data(snapshot):
            """快照行情数据回调"""
            self.data_count['market_data'] += 1
            if self.data_count['market_data'] <= 5:  # 只打印前5条
                self.logger.info(f"收到快照行情: {snapshot.stock_code} "
                               f"价格={snapshot.last_price} "
                               f"成交量={snapshot.volume}")
        
        def on_transaction(transaction):
            """逐笔成交数据回调"""
            self.data_count['transaction'] += 1
            if self.data_count['transaction'] <= 5:  # 只打印前5条
                self.logger.info(f"收到逐笔成交: {transaction.stock_code} "
                               f"价格={transaction.price} "
                               f"成交量={transaction.volume}")
        
        def on_order_detail(order_detail):
            """逐笔委托数据回调"""
            self.data_count['order_detail'] += 1
            if self.data_count['order_detail'] <= 5:  # 只打印前5条
                self.logger.info(f"收到逐笔委托: {order_detail.stock_code} "
                               f"价格={order_detail.price} "
                               f"委托量={order_detail.volume} "
                               f"方向={order_detail.side}")
        
        # 注册回调函数
        self.receiver.add_data_callback('market_data', on_market_data)
        self.receiver.add_data_callback('transaction', on_transaction)
        self.receiver.add_data_callback('order_detail', on_order_detail)
    
    def test_connection(self) -> bool:
        """测试连接功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试Level2连接...")
        
        try:
            # 启动接收器
            if not self.receiver.start():
                self.logger.error("Level2接收器启动失败")
                return False
            
            # 等待连接和登录
            max_wait_time = 30  # 最大等待30秒
            wait_time = 0
            
            while wait_time < max_wait_time:
                status = self.receiver.get_status()
                
                if status['is_logged_in']:
                    self.logger.info("Level2连接和登录成功")
                    return True
                
                if not status['is_running']:
                    self.logger.error("Level2接收器已停止运行")
                    return False
                
                time.sleep(1)
                wait_time += 1
                
                if wait_time % 5 == 0:
                    self.logger.info(f"等待连接中... ({wait_time}/{max_wait_time}秒)")
            
            self.logger.error("连接超时")
            return False
            
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False
    
    def test_subscription(self) -> bool:
        """测试订阅功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试Level2订阅...")
        
        try:
            # 测试快照行情订阅
            if not self.receiver.subscribe_market_data(['000001', '600000'], 'COMM'):
                self.logger.error("快照行情订阅失败")
                return False
            
            # 测试深圳逐笔数据订阅
            if not self.receiver.subscribe_transaction(['000001'], 'SZSE'):
                self.logger.warning("深圳逐笔成交订阅失败（可能不支持）")
            
            if not self.receiver.subscribe_order_detail(['000001'], 'SZSE'):
                self.logger.warning("深圳逐笔委托订阅失败（可能不支持）")
            
            self.logger.info("订阅测试完成")
            return True
            
        except Exception as e:
            self.logger.error(f"订阅测试失败: {e}")
            return False
    
    def test_data_reception(self, duration: int = 60) -> bool:
        """测试数据接收功能
        
        Args:
            duration: 测试持续时间（秒）
            
        Returns:
            bool: 测试是否成功
        """
        self.logger.info(f"开始测试数据接收，持续{duration}秒...")
        
        start_time = time.time()
        last_stats_time = start_time
        
        try:
            while time.time() - start_time < duration:
                # 每10秒打印一次统计信息
                if time.time() - last_stats_time >= 10:
                    stats = self.receiver.get_statistics()
                    self.logger.info(f"数据接收统计: "
                                   f"快照={stats.get('market_data_count', 0)} "
                                   f"成交={stats.get('transaction_count', 0)} "
                                   f"委托={stats.get('order_detail_count', 0)}")
                    last_stats_time = time.time()
                
                time.sleep(1)
            
            # 最终统计
            final_stats = self.receiver.get_statistics()
            self.logger.info(f"数据接收测试完成，最终统计: "
                           f"快照={final_stats.get('market_data_count', 0)} "
                           f"成交={final_stats.get('transaction_count', 0)} "
                           f"委托={final_stats.get('order_detail_count', 0)}")
            
            # 判断是否接收到数据
            total_data = (final_stats.get('market_data_count', 0) + 
                         final_stats.get('transaction_count', 0) + 
                         final_stats.get('order_detail_count', 0))
            
            if total_data > 0:
                self.logger.info("数据接收测试成功")
                return True
            else:
                self.logger.warning("未接收到任何数据，可能是非交易时间或配置问题")
                return False
                
        except Exception as e:
            self.logger.error(f"数据接收测试失败: {e}")
            return False
    
    def run_full_test(self, data_duration: int = 60) -> bool:
        """运行完整测试
        
        Args:
            data_duration: 数据接收测试持续时间
            
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始Level2数据接收器完整测试")
        
        try:
            # 1. 测试连接
            if not self.test_connection():
                return False
            
            # 2. 测试订阅
            if not self.test_subscription():
                return False
            
            # 3. 测试数据接收
            if not self.test_data_reception(data_duration):
                return False
            
            self.logger.info("Level2数据接收器完整测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"完整测试失败: {e}")
            return False
        finally:
            # 清理资源
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.receiver:
                self.receiver.stop()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Level2数据接收器测试")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--duration", "-d", type=int, default=60, help="数据接收测试持续时间（秒）")
    parser.add_argument("--connection-only", action="store_true", help="仅测试连接")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = Level2ReceiverTester(args.config)
    
    try:
        if args.connection_only:
            # 仅测试连接
            success = tester.test_connection()
        else:
            # 运行完整测试
            success = tester.run_full_test(args.duration)
        
        if success:
            print("✅ 测试成功")
            sys.exit(0)
        else:
            print("❌ 测试失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"测试异常: {e}")
        tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
