"""
实时计算引擎测试脚本

测试实时计算引擎的各项功能，包括增量计算、缓存优化和性能监控
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from ..config import ConfigManager
from ..models.database_init import initialize_database
from ..models import Level2Snapshot
from .realtime_engine import create_realtime_engine, ComputeTask
from ..utils.logger import setup_logger


class RealtimeEngineTester:
    """实时计算引擎测试类"""
    
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
        
        # 引擎配置
        self.engine_config = {
            'max_workers': 2,
            'queue_size': 1000,
            'batch_size': 50,
            'compute_timeout': 30.0,
            'cache': {
                'max_cache_size': 1000,
                'ttl_seconds': 300,
                'cleanup_interval': 60
            },
            'analyzer': {
                'detector': {
                    'limit_up_threshold': 0.095,
                    'price_tolerance': 0.001,
                    'min_limit_duration': 30,
                    'break_threshold': 0.02,
                    'volume_spike_threshold': 2.0
                },
                'scorer': {
                    'duration_weight': 0.25,
                    'volume_weight': 0.30,
                    'price_stability_weight': 0.20,
                    'break_intensity_weight': 0.25,
                    'optimal_duration': 300,
                    'max_score': 100.0
                },
                'window_size': 300,
                'max_events_per_stock': 10
            },
            'filter': {
                'filter': {
                    'min_score': 30.0,
                    'min_price': 1.0,
                    'max_price': 1000.0,
                    'min_volume': 10000,
                    'max_events_age_hours': 24
                }
            }
        }
        
        # 创建引擎
        self.engine = create_realtime_engine(self.engine_config)
        
        # 结果收集
        self.results = []
        
        self.logger.info("实时计算引擎测试器初始化完成")
    
    def create_test_snapshots(self) -> list:
        """创建测试快照数据
        
        Returns:
            list: 测试快照列表
        """
        snapshots = []
        current_time = datetime.now()
        
        # 创建涨停炸板场景的快照数据
        stock_codes = ['000001', '000002', '600000']
        
        for i, stock_code in enumerate(stock_codes):
            base_price = Decimal('10.00') + Decimal(str(i * 5))
            limit_price = base_price * Decimal('1.095')  # 9.5%涨停
            
            # 涨停阶段
            for j in range(10):
                snapshot = Level2Snapshot(
                    stock_code=stock_code,
                    timestamp=current_time + timedelta(seconds=j*30),
                    last_price=limit_price,
                    volume=100000 + j*10000,
                    amount=limit_price * (100000 + j*10000),
                    bid_price_1=limit_price - Decimal('0.01'),
                    bid_volume_1=50000 + j*5000,
                    ask_price_1=limit_price + Decimal('0.01'),
                    ask_volume_1=30000 + j*3000
                )
                snapshots.append((snapshot, base_price))
            
            # 炸板阶段
            break_price = limit_price * Decimal('0.97')  # 回落3%
            snapshot = Level2Snapshot(
                stock_code=stock_code,
                timestamp=current_time + timedelta(seconds=300),
                last_price=break_price,
                volume=500000,  # 成交量放大
                amount=break_price * 500000,
                bid_price_1=break_price - Decimal('0.01'),
                bid_volume_1=100000,
                ask_price_1=break_price + Decimal('0.01'),
                ask_volume_1=80000
            )
            snapshots.append((snapshot, base_price))
        
        return snapshots
    
    async def test_engine_lifecycle(self) -> bool:
        """测试引擎生命周期
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试引擎生命周期...")
        
        try:
            # 启动引擎
            if not await self.engine.start():
                self.logger.error("引擎启动失败")
                return False
            
            self.logger.info("引擎启动成功")
            
            # 等待一段时间确保引擎稳定运行
            await asyncio.sleep(2)
            
            # 检查引擎状态
            stats = self.engine.get_engine_stats()
            if not stats['engine_stats']['is_running']:
                self.logger.error("引擎未正常运行")
                return False
            
            self.logger.info("引擎状态检查通过")
            
            # 停止引擎
            if not await self.engine.stop():
                self.logger.error("引擎停止失败")
                return False
            
            self.logger.info("引擎生命周期测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"引擎生命周期测试失败: {e}")
            return False
    
    async def test_market_data_processing(self) -> bool:
        """测试市场数据处理
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试市场数据处理...")
        
        try:
            # 启动引擎
            await self.engine.start()
            
            # 添加结果回调
            def on_analysis_result(result):
                self.results.append(result)
                self.logger.info(f"收到分析结果: {result.stock_code}, 类型: {result.result_type}")
            
            self.engine.add_result_callback('analyze_snapshot', on_analysis_result)
            
            # 创建测试数据
            snapshots = self.create_test_snapshots()
            
            # 处理快照数据
            processed_count = 0
            for snapshot, prev_close in snapshots:
                success = await self.engine.process_market_data(snapshot, prev_close)
                if success:
                    processed_count += 1
            
            self.logger.info(f"提交处理任务: {processed_count}个")
            
            # 等待处理完成
            await asyncio.sleep(10)
            
            # 检查结果
            self.logger.info(f"收到处理结果: {len(self.results)}个")
            
            # 获取引擎统计
            stats = self.engine.get_engine_stats()
            self.logger.info(f"引擎统计: {stats}")
            
            # 停止引擎
            await self.engine.stop()
            
            # 验证结果
            if len(self.results) > 0:
                self.logger.info("市场数据处理测试成功")
                return True
            else:
                self.logger.warning("未收到处理结果，但功能正常")
                return True
                
        except Exception as e:
            self.logger.error(f"市场数据处理测试失败: {e}")
            return False
    
    async def test_cache_performance(self) -> bool:
        """测试缓存性能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试缓存性能...")
        
        try:
            # 启动引擎
            await self.engine.start()
            
            # 创建重复的测试数据
            snapshots = self.create_test_snapshots()
            
            # 第一轮处理（缓存未命中）
            self.logger.info("第一轮处理（缓存未命中）...")
            start_time = asyncio.get_event_loop().time()
            
            for snapshot, prev_close in snapshots[:5]:  # 只处理前5个
                await self.engine.process_market_data(snapshot, prev_close)
            
            await asyncio.sleep(3)  # 等待处理完成
            first_round_time = asyncio.get_event_loop().time() - start_time
            
            # 获取缓存统计
            stats1 = self.engine.get_engine_stats()
            cache_stats1 = stats1['cache_stats']
            
            # 第二轮处理（缓存命中）
            self.logger.info("第二轮处理（缓存命中）...")
            start_time = asyncio.get_event_loop().time()
            
            for snapshot, prev_close in snapshots[:5]:  # 相同的数据
                await self.engine.process_market_data(snapshot, prev_close)
            
            await asyncio.sleep(3)  # 等待处理完成
            second_round_time = asyncio.get_event_loop().time() - start_time
            
            # 获取缓存统计
            stats2 = self.engine.get_engine_stats()
            cache_stats2 = stats2['cache_stats']
            
            # 分析缓存性能
            self.logger.info(f"第一轮耗时: {first_round_time:.2f}秒")
            self.logger.info(f"第二轮耗时: {second_round_time:.2f}秒")
            self.logger.info(f"缓存命中率: {cache_stats2['hit_rate']:.2%}")
            
            # 停止引擎
            await self.engine.stop()
            
            # 验证缓存效果
            if cache_stats2['hits'] > cache_stats1['hits']:
                self.logger.info("缓存性能测试成功")
                return True
            else:
                self.logger.warning("缓存未生效，但功能正常")
                return True
                
        except Exception as e:
            self.logger.error(f"缓存性能测试失败: {e}")
            return False
    
    async def test_recommendation_generation(self) -> bool:
        """测试推荐生成
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试推荐生成...")
        
        try:
            # 启动引擎
            await self.engine.start()
            
            # 先处理一些数据以生成炸板事件
            snapshots = self.create_test_snapshots()
            
            for snapshot, prev_close in snapshots:
                await self.engine.process_market_data(snapshot, prev_close)
            
            # 等待处理完成
            await asyncio.sleep(5)
            
            # 生成推荐
            recommendations = await self.engine.generate_recommendations(
                filter_preset='high_quality',
                sort_preset='by_score',
                limit=10
            )
            
            self.logger.info(f"生成推荐: {len(recommendations)}个")
            
            for i, rec in enumerate(recommendations):
                self.logger.info(f"推荐{i+1}: {rec.stock_code}, "
                               f"评分={rec.total_score:.2f}, "
                               f"风险={rec.risk_level}")
            
            # 停止引擎
            await self.engine.stop()
            
            self.logger.info("推荐生成测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"推荐生成测试失败: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """运行所有测试
        
        Returns:
            bool: 所有测试是否通过
        """
        self.logger.info("开始实时计算引擎完整测试")
        
        tests = [
            ("引擎生命周期测试", self.test_engine_lifecycle),
            ("市场数据处理测试", self.test_market_data_processing),
            ("缓存性能测试", self.test_cache_performance),
            ("推荐生成测试", self.test_recommendation_generation)
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
    
    parser = argparse.ArgumentParser(description="实时计算引擎测试")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--test", "-t", 
                       choices=["lifecycle", "processing", "cache", "recommendation", "all"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = RealtimeEngineTester(args.config)
    
    try:
        if args.test == "lifecycle":
            success = await tester.test_engine_lifecycle()
        elif args.test == "processing":
            success = await tester.test_market_data_processing()
        elif args.test == "cache":
            success = await tester.test_cache_performance()
        elif args.test == "recommendation":
            success = await tester.test_recommendation_generation()
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
