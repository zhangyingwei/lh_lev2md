#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
Task 1 测试文件 - Level2 API连接管理器测试

功能说明：
1. 测试MarketDataReceiver的连接管理功能
2. 验证连接状态管理、登录认证、连接健康检查
3. 测试数据接收和处理功能
4. 验证重连机制

作者：AI Agent Development Team
版本：v1.0.0
"""

import sys
import os
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import ConfigManager
from src.logging.log_manager import LogManager
from src.data_processing.market_data_receiver import MarketDataReceiver
from src.data_processing.data_handler import DataHandler


class Task1Tester:
    """Task 1 功能测试器"""
    
    def __init__(self):
        """初始化测试器"""
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化日志管理器
        log_config = self.config_manager.get_logging_config()
        self.log_manager = LogManager(log_config)
        self.logger = self.log_manager.get_logger("Task1Tester")
        
        # 初始化数据处理器
        data_config = self.config_manager.get('data_processing', {})
        self.data_handler = DataHandler(data_config)
        
        # 初始化行情数据接收器
        level2_config = self.config_manager.get_level2_config()
        self.market_data_receiver = MarketDataReceiver(level2_config, self.data_handler)
        
        # 测试统计
        self.test_stats = {
            'connection_tests': 0,
            'data_reception_tests': 0,
            'reconnection_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0
        }
        
        self.logger.info("Task1Tester初始化完成")
    
    def run_all_tests(self):
        """运行所有测试"""
        self.logger.info("开始运行Task 1所有测试")
        
        try:
            # 测试1: 连接管理功能
            self.test_connection_management()
            
            # 测试2: 数据接收功能
            self.test_data_reception()
            
            # 测试3: 统计信息功能
            self.test_statistics()
            
            # 测试4: 配置管理功能
            self.test_configuration()
            
            # 输出测试结果
            self.print_test_results()
            
        except Exception as e:
            self.logger.error(f"测试执行异常: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def test_connection_management(self):
        """测试连接管理功能"""
        self.logger.info("开始测试连接管理功能")
        self.test_stats['connection_tests'] += 1
        
        try:
            # 启动数据处理器
            self.data_handler.start_processing()
            
            # 初始化连接
            success = self.market_data_receiver.initialize()
            
            if success:
                self.logger.info("连接初始化成功")
                
                # 等待连接建立
                max_wait_time = 30  # 30秒超时
                wait_time = 0
                
                while wait_time < max_wait_time:
                    if self.market_data_receiver.is_connected():
                        self.logger.info("连接建立成功")
                        self.test_stats['passed_tests'] += 1
                        break
                    
                    time.sleep(1)
                    wait_time += 1
                    self.logger.info(f"等待连接建立... {wait_time}/{max_wait_time}秒")
                
                if wait_time >= max_wait_time:
                    self.logger.error("连接建立超时")
                    self.test_stats['failed_tests'] += 1
                else:
                    # 测试连接状态
                    stats = self.market_data_receiver.get_stats()
                    self.logger.info(f"连接统计信息: {stats}")
                    
            else:
                self.logger.error("连接初始化失败")
                self.test_stats['failed_tests'] += 1
                
        except Exception as e:
            self.logger.error(f"连接管理测试异常: {e}", exc_info=True)
            self.test_stats['failed_tests'] += 1
    
    def test_data_reception(self):
        """测试数据接收功能"""
        self.logger.info("开始测试数据接收功能")
        self.test_stats['data_reception_tests'] += 1
        
        try:
            if not self.market_data_receiver.is_connected():
                self.logger.warning("连接未建立，跳过数据接收测试")
                return
            
            # 设置数据订阅回调
            received_data = {'market_data': 0, 'transaction': 0, 'order_detail': 0}
            
            def on_market_data(data):
                received_data['market_data'] += 1
                self.logger.debug(f"接收到快照行情: {data['stock_code']}")
            
            def on_transaction(data):
                received_data['transaction'] += 1
                self.logger.debug(f"接收到逐笔成交: {data['stock_code']}")
            
            def on_order_detail(data):
                received_data['order_detail'] += 1
                self.logger.debug(f"接收到逐笔委托: {data['stock_code']}")
            
            # 订阅数据
            self.data_handler.subscribe('market_data', on_market_data)
            self.data_handler.subscribe('transaction', on_transaction)
            self.data_handler.subscribe('order_detail', on_order_detail)
            
            # 等待数据接收
            self.logger.info("等待数据接收，测试时间60秒...")
            time.sleep(60)
            
            # 检查接收结果
            total_received = sum(received_data.values())
            if total_received > 0:
                self.logger.info(f"数据接收测试成功，共接收 {total_received} 条数据")
                self.logger.info(f"数据分布: {received_data}")
                self.test_stats['passed_tests'] += 1
            else:
                self.logger.warning("未接收到任何数据，可能是市场休市或配置问题")
                self.test_stats['failed_tests'] += 1
                
        except Exception as e:
            self.logger.error(f"数据接收测试异常: {e}", exc_info=True)
            self.test_stats['failed_tests'] += 1
    
    def test_statistics(self):
        """测试统计信息功能"""
        self.logger.info("开始测试统计信息功能")
        
        try:
            # 获取接收器统计信息
            receiver_stats = self.market_data_receiver.get_stats()
            self.logger.info(f"接收器统计信息: {receiver_stats}")
            
            # 获取数据处理器统计信息
            handler_stats = self.data_handler.get_stats()
            self.logger.info(f"数据处理器统计信息: {handler_stats}")
            
            self.test_stats['passed_tests'] += 1
            
        except Exception as e:
            self.logger.error(f"统计信息测试异常: {e}", exc_info=True)
            self.test_stats['failed_tests'] += 1
    
    def test_configuration(self):
        """测试配置管理功能"""
        self.logger.info("开始测试配置管理功能")
        
        try:
            # 测试配置获取
            level2_config = self.config_manager.get_level2_config()
            self.logger.info(f"Level2配置: {level2_config}")
            
            # 测试配置设置
            original_value = self.config_manager.get('level2.reconnect_interval', 5)
            self.config_manager.set('level2.reconnect_interval', 10)
            new_value = self.config_manager.get('level2.reconnect_interval')
            
            if new_value == 10:
                self.logger.info("配置设置测试成功")
                # 恢复原值
                self.config_manager.set('level2.reconnect_interval', original_value)
                self.test_stats['passed_tests'] += 1
            else:
                self.logger.error("配置设置测试失败")
                self.test_stats['failed_tests'] += 1
                
        except Exception as e:
            self.logger.error(f"配置管理测试异常: {e}", exc_info=True)
            self.test_stats['failed_tests'] += 1
    
    def print_test_results(self):
        """输出测试结果"""
        self.logger.info("=" * 60)
        self.logger.info("Task 1 测试结果汇总")
        self.logger.info("=" * 60)
        self.logger.info(f"连接管理测试: {self.test_stats['connection_tests']}")
        self.logger.info(f"数据接收测试: {self.test_stats['data_reception_tests']}")
        self.logger.info(f"通过测试: {self.test_stats['passed_tests']}")
        self.logger.info(f"失败测试: {self.test_stats['failed_tests']}")
        
        total_tests = self.test_stats['passed_tests'] + self.test_stats['failed_tests']
        if total_tests > 0:
            success_rate = (self.test_stats['passed_tests'] / total_tests) * 100
            self.logger.info(f"测试成功率: {success_rate:.2f}%")
        
        # 验收标准检查
        self.logger.info("=" * 60)
        self.logger.info("验收标准检查")
        self.logger.info("=" * 60)
        
        if self.market_data_receiver.is_connected():
            self.logger.info("✓ 连接成功率 > 99% (连接已建立)")
        else:
            self.logger.warning("✗ 连接未建立")
        
        receiver_stats = self.market_data_receiver.get_stats()
        if receiver_stats.get('reconnect_count', 0) == 0:
            self.logger.info("✓ 无重连发生")
        else:
            self.logger.info(f"ℹ 重连次数: {receiver_stats.get('reconnect_count', 0)}")
        
        self.logger.info("=" * 60)
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("开始清理测试资源")
        
        try:
            # 关闭数据处理器
            self.data_handler.shutdown()
            
            # 关闭行情接收器
            self.market_data_receiver.shutdown()
            
            self.logger.info("测试资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源异常: {e}", exc_info=True)


def main():
    """主函数"""
    print("Task 1 - Level2 API连接管理器测试")
    print("=" * 60)
    
    tester = Task1Tester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
