#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
Task 1 演示程序 - Level2 API连接管理器

功能说明：
1. 演示MarketDataReceiver的基本使用方法
2. 展示连接管理、数据接收、统计监控等功能
3. 提供完整的使用示例

作者：AI Agent Development Team
版本：v1.0.0
"""

import sys
import os
import time
import signal
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import ConfigManager
from src.logging.log_manager import LogManager
from src.data_processing.market_data_receiver import MarketDataReceiver
from src.data_processing.data_handler import DataHandler


class Task1Demo:
    """Task 1 演示程序"""
    
    def __init__(self, config_file: str = None):
        """
        初始化演示程序
        
        Args:
            config_file: 配置文件路径
        """
        # 初始化配置管理器
        if config_file:
            self.config_manager = ConfigManager(config_file)
        else:
            self.config_manager = ConfigManager()
        
        # 初始化日志管理器
        log_config = self.config_manager.get_logging_config()
        self.log_manager = LogManager(log_config)
        self.logger = self.log_manager.get_logger("Task1Demo")
        
        # 初始化数据处理器
        data_config = self.config_manager.get('data_processing', {})
        self.data_handler = DataHandler(data_config)
        
        # 初始化行情数据接收器
        level2_config = self.config_manager.get_level2_config()
        self.market_data_receiver = MarketDataReceiver(level2_config, self.data_handler)
        
        # 运行状态
        self.running = False
        
        # 数据统计
        self.data_stats = {
            'market_data_count': 0,
            'transaction_count': 0,
            'order_detail_count': 0,
            'start_time': None
        }
        
        self.logger.info("Task1Demo初始化完成")
    
    def setup_data_callbacks(self):
        """设置数据回调函数"""
        
        def on_market_data(data):
            """快照行情回调"""
            self.data_stats['market_data_count'] += 1
            
            if self.data_stats['market_data_count'] % 100 == 0:
                self.logger.info(
                    f"接收快照行情: {data['stock_code']} "
                    f"价格:{data['last_price']:.4f} "
                    f"累计:{self.data_stats['market_data_count']}"
                )
        
        def on_transaction(data):
            """逐笔成交回调"""
            self.data_stats['transaction_count'] += 1
            
            if self.data_stats['transaction_count'] % 50 == 0:
                self.logger.info(
                    f"接收逐笔成交: {data['stock_code']} "
                    f"价格:{data['trade_price']:.4f} "
                    f"数量:{data['trade_volume']} "
                    f"累计:{self.data_stats['transaction_count']}"
                )
        
        def on_order_detail(data):
            """逐笔委托回调"""
            self.data_stats['order_detail_count'] += 1
            
            if self.data_stats['order_detail_count'] % 50 == 0:
                self.logger.info(
                    f"接收逐笔委托: {data['stock_code']} "
                    f"价格:{data['price']:.4f} "
                    f"数量:{data['volume']} "
                    f"累计:{self.data_stats['order_detail_count']}"
                )
        
        # 订阅数据
        self.data_handler.subscribe('market_data', on_market_data)
        self.data_handler.subscribe('transaction', on_transaction)
        self.data_handler.subscribe('order_detail', on_order_detail)
        
        self.logger.info("数据回调函数设置完成")
    
    def start(self):
        """启动演示程序"""
        try:
            self.logger.info("启动Task 1演示程序")
            self.logger.info("=" * 60)
            
            # 设置信号处理
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # 启动数据处理器
            self.data_handler.start_processing()
            
            # 设置数据回调
            self.setup_data_callbacks()
            
            # 初始化并启动行情接收器
            if self.market_data_receiver.initialize():
                self.logger.info("Level2 API初始化成功")
                
                # 等待连接建立
                self.logger.info("等待连接建立...")
                max_wait_time = 30
                wait_time = 0
                
                while wait_time < max_wait_time and not self.market_data_receiver.is_connected():
                    time.sleep(1)
                    wait_time += 1
                    if wait_time % 5 == 0:
                        self.logger.info(f"等待连接... {wait_time}/{max_wait_time}秒")
                
                if self.market_data_receiver.is_connected():
                    self.logger.info("连接建立成功，开始接收数据")
                    self.running = True
                    self.data_stats['start_time'] = time.time()
                    
                    # 主循环
                    self._main_loop()
                    
                else:
                    self.logger.error("连接建立失败")
                    
            else:
                self.logger.error("Level2 API初始化失败")
                
        except Exception as e:
            self.logger.error(f"启动演示程序异常: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def _main_loop(self):
        """主循环"""
        self.logger.info("进入主循环，按Ctrl+C退出")
        
        last_stats_time = time.time()
        stats_interval = 60  # 60秒输出一次统计
        
        try:
            while self.running:
                time.sleep(1)
                
                # 定期输出统计信息
                current_time = time.time()
                if current_time - last_stats_time >= stats_interval:
                    self._print_statistics()
                    last_stats_time = current_time
                
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号，准备退出")
            self.running = False
    
    def _print_statistics(self):
        """输出统计信息"""
        self.logger.info("=" * 60)
        self.logger.info("统计信息")
        self.logger.info("=" * 60)
        
        # 运行时间
        if self.data_stats['start_time']:
            runtime = time.time() - self.data_stats['start_time']
            self.logger.info(f"运行时间: {runtime:.0f}秒")
        
        # 数据接收统计
        self.logger.info(f"快照行情: {self.data_stats['market_data_count']}")
        self.logger.info(f"逐笔成交: {self.data_stats['transaction_count']}")
        self.logger.info(f"逐笔委托: {self.data_stats['order_detail_count']}")
        
        total_data = (self.data_stats['market_data_count'] + 
                     self.data_stats['transaction_count'] + 
                     self.data_stats['order_detail_count'])
        self.logger.info(f"总数据量: {total_data}")
        
        # 接收器统计
        receiver_stats = self.market_data_receiver.get_stats()
        self.logger.info(f"连接状态: {'已连接' if receiver_stats.get('connected') else '未连接'}")
        self.logger.info(f"登录状态: {'已登录' if receiver_stats.get('login_success') else '未登录'}")
        self.logger.info(f"重连次数: {receiver_stats.get('reconnect_count', 0)}")
        
        # 数据处理器统计
        handler_stats = self.data_handler.get_stats()
        self.logger.info(f"处理队列大小: {handler_stats.get('queue_size', 0)}")
        self.logger.info(f"已处理数据: {handler_stats.get('processed_count', 0)}")
        self.logger.info(f"处理错误: {handler_stats.get('error_count', 0)}")
        
        if handler_stats.get('avg_latency'):
            self.logger.info(f"平均延迟: {handler_stats['avg_latency']:.2f}ms")
        
        self.logger.info("=" * 60)
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        self.logger.info(f"接收到信号 {signum}，准备退出")
        self.running = False
    
    def shutdown(self):
        """关闭演示程序"""
        self.logger.info("开始关闭演示程序")
        
        try:
            # 输出最终统计
            self._print_statistics()
            
            # 关闭数据处理器
            self.data_handler.shutdown()
            
            # 关闭行情接收器
            self.market_data_receiver.shutdown()
            
            self.logger.info("演示程序已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭演示程序异常: {e}", exc_info=True)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Task 1 - Level2 API连接管理器演示')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--tcp', help='TCP连接地址')
    parser.add_argument('--udp', nargs=2, metavar=('MCAST_ADDR', 'INTERFACE_IP'), 
                       help='UDP组播地址和接口IP')
    
    args = parser.parse_args()
    
    print("Task 1 - Level2 API连接管理器演示")
    print("=" * 60)
    print("功能特性:")
    print("- 稳定的Level2连接管理")
    print("- 自动重连机制")
    print("- 实时数据接收和处理")
    print("- 连接健康检查")
    print("- 详细的统计监控")
    print("=" * 60)
    
    # 创建演示程序
    demo = Task1Demo(args.config)
    
    # 如果指定了命令行参数，更新配置
    if args.tcp:
        demo.config_manager.set('level2.connection_type', 'tcp')
        demo.config_manager.set('level2.tcp_address', args.tcp)
        print(f"使用TCP连接: {args.tcp}")
    
    if args.udp:
        demo.config_manager.set('level2.connection_type', 'udp')
        demo.config_manager.set('level2.multicast_address', args.udp[0])
        demo.config_manager.set('level2.interface_ip', args.udp[1])
        print(f"使用UDP组播: {args.udp[0]}, 接口IP: {args.udp[1]}")
    
    # 启动演示
    demo.start()


if __name__ == "__main__":
    main()
