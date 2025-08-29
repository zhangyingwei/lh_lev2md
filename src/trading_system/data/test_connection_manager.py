"""
连接管理器测试脚本

测试连接管理器的各项功能，包括连接状态管理、自动重连机制、
健康检查、质量监控和异常恢复处理
"""

import asyncio
import time
from datetime import datetime

from ..config import ConfigManager
from ..models.database_init import initialize_database
from .connection_manager import create_connection_manager, ConnectionState
from .level2_service import create_level2_service
from .mock_level2_receiver import MockLevel2DataReceiver
from ..utils.logger import setup_logger


class ConnectionManagerTester:
    """连接管理器测试类"""
    
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
        
        # 连接管理器配置
        self.connection_config = {
            'max_reconnect_attempts': 5,
            'reconnect_initial_delay': 1.0,
            'reconnect_max_delay': 10.0,
            'reconnect_backoff_factor': 2.0,
            'reconnect_jitter': True,
            'health_check_enabled': True,
            'health_check_interval': 5.0,
            'quality_monitor_enabled': True,
            'quality_monitor_interval': 10.0,
            'failure_detection_enabled': True,
            'max_no_data_time': 30.0,
            'min_data_rate': 0.1
        }
        
        self.logger.info("连接管理器测试器初始化完成")
    
    async def test_basic_connection_management(self) -> bool:
        """测试基本连接管理功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试基本连接管理功能...")
        
        try:
            # 创建连接管理器
            manager = create_connection_manager(self.connection_config)
            
            # 创建模拟接收器
            mock_receiver = MockLevel2DataReceiver({'connection_mode': 'mock'})
            manager.set_connection_instance(mock_receiver)
            
            # 启动监控
            if not await manager.start_monitoring():
                self.logger.error("连接监控启动失败")
                return False
            
            # 测试连接建立
            manager.on_connection_established()
            status = manager.get_connection_status()
            if status['state'] != ConnectionState.CONNECTED.value:
                self.logger.error(f"连接状态错误: {status['state']}")
                return False
            
            # 测试认证成功
            manager.on_authentication_success()
            status = manager.get_connection_status()
            if status['state'] != ConnectionState.AUTHENTICATED.value:
                self.logger.error(f"认证状态错误: {status['state']}")
                return False
            
            # 测试数据接收
            for i in range(10):
                manager.on_data_received('market_data', 1)
                await asyncio.sleep(0.1)
            
            # 检查健康状态
            health = manager.get_health_status()
            if not health['is_healthy']:
                self.logger.error("健康检查失败")
                return False
            
            # 停止监控
            await manager.stop_monitoring()
            
            self.logger.info("基本连接管理功能测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"基本连接管理功能测试失败: {e}")
            return False
    
    async def test_reconnect_mechanism(self) -> bool:
        """测试重连机制
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试重连机制...")
        
        try:
            # 创建连接管理器
            reconnect_config = self.connection_config.copy()
            reconnect_config['max_reconnect_attempts'] = 3
            reconnect_config['reconnect_initial_delay'] = 0.5
            
            manager = create_connection_manager(reconnect_config)
            
            # 创建模拟接收器
            mock_receiver = MockLevel2DataReceiver({'connection_mode': 'mock'})
            manager.set_connection_instance(mock_receiver)
            
            # 启动监控
            await manager.start_monitoring()
            
            # 建立连接
            manager.on_connection_established()
            manager.on_authentication_success()
            
            # 记录重连事件
            reconnect_events = []
            
            def on_reconnect_start(attempt, delay):
                reconnect_events.append(('start', attempt, delay))
                self.logger.info(f"重连开始: 第{attempt}次, 延迟{delay:.1f}秒")
            
            def on_reconnect_success(attempt):
                reconnect_events.append(('success', attempt))
                self.logger.info(f"重连成功: 第{attempt}次")
            
            def on_reconnect_failed(attempt):
                reconnect_events.append(('failed', attempt))
                self.logger.info(f"重连失败: 第{attempt}次")
            
            manager.add_event_callback('on_reconnect_start', on_reconnect_start)
            manager.add_event_callback('on_reconnect_success', on_reconnect_success)
            manager.add_event_callback('on_reconnect_failed', on_reconnect_failed)
            
            # 模拟连接丢失
            self.logger.info("模拟连接丢失...")
            manager.on_connection_lost(1001)
            
            # 等待重连过程
            await asyncio.sleep(8)
            
            # 检查重连事件
            if not reconnect_events:
                self.logger.error("没有触发重连事件")
                return False
            
            # 检查是否有重连开始事件
            start_events = [e for e in reconnect_events if e[0] == 'start']
            if not start_events:
                self.logger.error("没有重连开始事件")
                return False
            
            self.logger.info(f"重连事件记录: {reconnect_events}")
            
            # 停止监控
            await manager.stop_monitoring()
            
            self.logger.info("重连机制测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"重连机制测试失败: {e}")
            return False
    
    async def test_health_monitoring(self) -> bool:
        """测试健康监控功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试健康监控功能...")
        
        try:
            # 创建连接管理器
            health_config = self.connection_config.copy()
            health_config['health_check_interval'] = 2.0
            health_config['max_no_data_time'] = 5.0
            
            manager = create_connection_manager(health_config)
            
            # 创建模拟接收器
            mock_receiver = MockLevel2DataReceiver({'connection_mode': 'mock'})
            manager.set_connection_instance(mock_receiver)
            
            # 启动监控
            await manager.start_monitoring()
            
            # 建立连接
            manager.on_connection_established()
            manager.on_authentication_success()
            
            # 正常数据接收
            for i in range(5):
                manager.on_data_received('market_data', 1)
                await asyncio.sleep(0.5)
            
            # 检查健康状态
            health = manager.get_health_status()
            if not health['is_healthy']:
                self.logger.error("正常情况下健康检查失败")
                return False
            
            self.logger.info("正常健康状态检查通过")
            
            # 模拟长时间无数据
            self.logger.info("模拟长时间无数据情况...")
            await asyncio.sleep(6)  # 超过max_no_data_time
            
            # 再次检查健康状态
            health = manager.get_health_status()
            self.logger.info(f"长时间无数据后的健康状态: {health}")
            
            # 停止监控
            await manager.stop_monitoring()
            
            self.logger.info("健康监控功能测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"健康监控功能测试失败: {e}")
            return False
    
    async def test_level2_service_integration(self) -> bool:
        """测试Level2服务集成
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试Level2服务集成...")
        
        try:
            # 创建服务配置
            service_config = {
                'level2': {
                    'connection_mode': 'mock',
                    'max_reconnect_attempts': 3,
                    'reconnect_initial_delay': 1.0
                },
                'performance': {
                    'batch_size': 10,
                    'flush_interval': 2.0,
                    'max_workers': 1
                },
                'database': {
                    'redis': {}
                },
                'monitoring': {
                    'health_check_enabled': True,
                    'health_check_interval': 3.0,
                    'quality_monitor_enabled': True
                }
            }
            
            # 创建Level2服务
            service = create_level2_service(service_config)
            
            # 启动服务
            if not await service.start():
                self.logger.error("Level2服务启动失败")
                return False
            
            # 订阅数据
            service.subscribe_market_data(['000001', '600000'])
            service.subscribe_transaction(['000001'])
            service.subscribe_order_detail(['000001'])
            
            # 运行一段时间
            self.logger.info("服务运行中，收集数据...")
            await asyncio.sleep(10)
            
            # 获取服务状态
            status = service.get_service_status()
            self.logger.info(f"服务状态: {status}")
            
            # 检查数据处理
            if status['service_stats']['total_data_processed'] == 0:
                self.logger.warning("未处理任何数据")
            else:
                self.logger.info(f"已处理数据: {status['service_stats']['total_data_processed']}条")
            
            # 测试强制重连
            self.logger.info("测试强制重连...")
            service.force_reconnect()
            await asyncio.sleep(3)
            
            # 测试缓存功能
            cached_data = service.get_cached_market_data('000001')
            if cached_data:
                self.logger.info(f"缓存数据获取成功: {cached_data}")
            
            # 强制刷新缓冲区
            if service.force_flush_buffer():
                self.logger.info("缓冲区刷新成功")
            
            # 停止服务
            await service.stop()
            
            self.logger.info("Level2服务集成测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Level2服务集成测试失败: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """运行所有测试
        
        Returns:
            bool: 所有测试是否通过
        """
        self.logger.info("开始连接管理器完整测试")
        
        tests = [
            ("基本连接管理功能测试", self.test_basic_connection_management),
            ("重连机制测试", self.test_reconnect_mechanism),
            ("健康监控功能测试", self.test_health_monitoring),
            ("Level2服务集成测试", self.test_level2_service_integration)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            self.logger.info(f"执行 {test_name}...")
            try:
                result = await test_func()
                results.append(result)
                if result:
                    self.logger.info(f"✅ {test_name} 通过")
                else:
                    self.logger.error(f"❌ {test_name} 失败")
            except Exception as e:
                self.logger.error(f"❌ {test_name} 异常: {e}")
                results.append(False)
            
            # 测试间隔
            await asyncio.sleep(1)
        
        success_count = sum(results)
        total_count = len(results)
        
        self.logger.info(f"测试完成: {success_count}/{total_count} 通过")
        
        return all(results)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="连接管理器测试")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--test", "-t", 
                       choices=["basic", "reconnect", "health", "integration", "all"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = ConnectionManagerTester(args.config)
    
    try:
        if args.test == "basic":
            success = await tester.test_basic_connection_management()
        elif args.test == "reconnect":
            success = await tester.test_reconnect_mechanism()
        elif args.test == "health":
            success = await tester.test_health_monitoring()
        elif args.test == "integration":
            success = await tester.test_level2_service_integration()
        else:
            success = await tester.run_all_tests()
        
        if success:
            print("✅ 所有测试通过")
            return 0
        else:
            print("❌ 部分测试失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"测试异常: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
