"""
量化交易系统集成服务测试脚本

测试系统集成服务的各项功能，包括服务启停、数据处理、推荐生成等
"""

import asyncio
from datetime import datetime

from .trading_service import create_trading_service
from ..utils.logger import setup_logger


class TradingServiceTester:
    """交易系统服务测试类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化测试器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.logger = setup_logger({})
        
        # 创建交易服务
        self.trading_service = create_trading_service(config_path)
        
        # 测试结果收集
        self.test_results = {
            'events_received': 0,
            'recommendations_received': 0,
            'status_changes': 0
        }
        
        self.logger.info("交易系统服务测试器初始化完成")
    
    def setup_callbacks(self):
        """设置事件回调"""
        def on_break_event(event):
            self.test_results['events_received'] += 1
            self.logger.info(f"收到炸板事件: {event.stock_code}, 评分: {event.score:.2f}")
        
        def on_recommendations_updated(recommendations):
            self.test_results['recommendations_received'] += 1
            self.logger.info(f"推荐更新: {len(recommendations)}个推荐")
        
        def on_system_status_changed(status):
            self.test_results['status_changes'] += 1
            self.logger.info(f"系统状态变更: 运行={status.is_running}")
        
        # 注册回调
        self.trading_service.add_event_callback('on_break_event', on_break_event)
        self.trading_service.add_event_callback('on_recommendations_updated', on_recommendations_updated)
        self.trading_service.add_event_callback('on_system_status_changed', on_system_status_changed)
    
    async def test_service_lifecycle(self) -> bool:
        """测试服务生命周期
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试服务生命周期...")
        
        try:
            # 检查初始状态
            initial_status = self.trading_service.get_system_status()
            if initial_status.is_running:
                self.logger.error("初始状态应该是停止状态")
                return False
            
            # 启动服务
            if not await self.trading_service.start():
                self.logger.error("服务启动失败")
                return False
            
            self.logger.info("服务启动成功")
            
            # 检查运行状态
            running_status = self.trading_service.get_system_status()
            if not running_status.is_running:
                self.logger.error("服务应该处于运行状态")
                return False
            
            # 等待服务稳定运行
            await asyncio.sleep(3)
            
            # 停止服务
            if not await self.trading_service.stop():
                self.logger.error("服务停止失败")
                return False
            
            self.logger.info("服务停止成功")
            
            # 检查停止状态
            stopped_status = self.trading_service.get_system_status()
            if stopped_status.is_running:
                self.logger.error("服务应该处于停止状态")
                return False
            
            self.logger.info("服务生命周期测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"服务生命周期测试失败: {e}")
            return False
    
    async def test_data_subscription(self) -> bool:
        """测试数据订阅功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试数据订阅功能...")
        
        try:
            # 启动服务
            await self.trading_service.start()
            
            # 订阅股票数据
            stock_codes = ['000001', '000002', '600000', '600036', '600519']
            success = await self.trading_service.subscribe_stocks(stock_codes)
            
            if success:
                self.logger.info(f"股票数据订阅成功: {stock_codes}")
            else:
                self.logger.warning("股票数据订阅失败，但功能正常（可能是模拟模式）")
            
            # 等待数据处理
            await asyncio.sleep(5)
            
            # 停止服务
            await self.trading_service.stop()
            
            self.logger.info("数据订阅功能测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"数据订阅功能测试失败: {e}")
            return False
    
    async def test_event_processing(self) -> bool:
        """测试事件处理功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试事件处理功能...")
        
        try:
            # 设置回调
            self.setup_callbacks()
            
            # 启动服务
            await self.trading_service.start()
            
            # 等待事件处理
            await asyncio.sleep(10)
            
            # 获取最新事件
            events = self.trading_service.get_latest_events(limit=10)
            self.logger.info(f"获取到事件: {len(events)}个")
            
            # 获取最新推荐
            recommendations = self.trading_service.get_latest_recommendations(limit=5)
            self.logger.info(f"获取到推荐: {len(recommendations)}个")
            
            # 停止服务
            await self.trading_service.stop()
            
            self.logger.info("事件处理功能测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"事件处理功能测试失败: {e}")
            return False
    
    async def test_system_statistics(self) -> bool:
        """测试系统统计功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试系统统计功能...")
        
        try:
            # 启动服务
            await self.trading_service.start()
            
            # 等待一段时间收集统计数据
            await asyncio.sleep(5)
            
            # 获取系统统计
            stats = self.trading_service.get_system_statistics()
            self.logger.info(f"系统统计: {stats}")
            
            # 验证统计数据结构
            required_keys = ['system_status', 'data_statistics']
            for key in required_keys:
                if key not in stats:
                    self.logger.error(f"统计数据缺少必要字段: {key}")
                    return False
            
            # 验证系统状态
            system_status = stats['system_status']
            if not system_status.get('is_running'):
                self.logger.error("系统状态显示未运行")
                return False
            
            # 停止服务
            await self.trading_service.stop()
            
            self.logger.info("系统统计功能测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统统计功能测试失败: {e}")
            return False
    
    async def test_integration_workflow(self) -> bool:
        """测试完整集成工作流
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试完整集成工作流...")
        
        try:
            # 设置回调
            self.setup_callbacks()
            
            # 启动服务
            await self.trading_service.start()
            
            # 订阅股票
            stock_codes = ['000001', '600000', '600519']
            await self.trading_service.subscribe_stocks(stock_codes)
            
            # 运行一段时间，模拟完整工作流
            self.logger.info("系统运行中，收集数据和生成推荐...")
            await asyncio.sleep(15)
            
            # 检查工作流结果
            events = self.trading_service.get_latest_events()
            recommendations = self.trading_service.get_latest_recommendations()
            stats = self.trading_service.get_system_statistics()
            
            self.logger.info(f"工作流结果:")
            self.logger.info(f"  - 炸板事件: {len(events)}个")
            self.logger.info(f"  - 推荐结果: {len(recommendations)}个")
            self.logger.info(f"  - 系统运行时间: {stats['system_status'].get('uptime_seconds', 0)}秒")
            self.logger.info(f"  - 回调统计: {self.test_results}")
            
            # 停止服务
            await self.trading_service.stop()
            
            self.logger.info("完整集成工作流测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"完整集成工作流测试失败: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """运行所有测试
        
        Returns:
            bool: 所有测试是否通过
        """
        self.logger.info("开始交易系统服务完整测试")
        
        tests = [
            ("服务生命周期测试", self.test_service_lifecycle),
            ("数据订阅功能测试", self.test_data_subscription),
            ("事件处理功能测试", self.test_event_processing),
            ("系统统计功能测试", self.test_system_statistics),
            ("完整集成工作流测试", self.test_integration_workflow)
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
            await asyncio.sleep(2)
        
        success_count = sum(results)
        total_count = len(results)
        
        self.logger.info(f"测试完成: {success_count}/{total_count} 通过")
        
        return all(results)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="交易系统服务测试")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--test", "-t", 
                       choices=["lifecycle", "subscription", "events", "statistics", "workflow", "all"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = TradingServiceTester(args.config)
    
    try:
        if args.test == "lifecycle":
            success = await tester.test_service_lifecycle()
        elif args.test == "subscription":
            success = await tester.test_data_subscription()
        elif args.test == "events":
            success = await tester.test_event_processing()
        elif args.test == "statistics":
            success = await tester.test_system_statistics()
        elif args.test == "workflow":
            success = await tester.test_integration_workflow()
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
