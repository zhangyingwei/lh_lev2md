"""
涨停炸板分析器测试脚本

测试涨停炸板检测、评分和分析功能
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from ..config import ConfigManager
from ..models.database_init import initialize_database
from ..models import Level2Snapshot
from .limit_up_break_analyzer import create_limit_up_analyzer
from ..utils.logger import setup_logger


class LimitUpAnalyzerTester:
    """涨停炸板分析器测试类"""
    
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
        
        # 分析器配置
        self.analyzer_config = {
            'detector': {
                'limit_up_threshold': 0.095,  # 9.5%涨幅
                'price_tolerance': 0.001,     # 0.1%价格容差
                'min_limit_duration': 30,     # 最小涨停30秒
                'break_threshold': 0.02,      # 2%回落阈值
                'volume_spike_threshold': 2.0  # 成交量激增阈值
            },
            'scorer': {
                'duration_weight': 0.25,
                'volume_weight': 0.30,
                'price_stability_weight': 0.20,
                'break_intensity_weight': 0.25,
                'optimal_duration': 300,  # 5分钟最佳持续时间
                'max_score': 100.0
            },
            'window_size': 300,  # 5分钟数据窗口
            'max_events_per_stock': 10
        }
        
        # 创建分析器
        self.analyzer = create_limit_up_analyzer(self.analyzer_config)
        
        self.logger.info("涨停炸板分析器测试器初始化完成")
    
    def create_test_snapshots(self, stock_code: str, base_price: Decimal, scenario: str) -> list:
        """创建测试快照数据
        
        Args:
            stock_code: 股票代码
            base_price: 基础价格
            scenario: 测试场景
            
        Returns:
            list: 快照数据列表
        """
        snapshots = []
        current_time = datetime.now()
        
        if scenario == "normal_limit_up_break":
            # 正常涨停炸板场景
            limit_price = base_price * Decimal('1.095')  # 9.5%涨停
            
            # 1. 涨停前的正常交易
            for i in range(10):
                price = base_price + Decimal(str(i * 0.01))
                snapshot = self._create_snapshot(
                    stock_code, current_time + timedelta(seconds=i*10), 
                    price, 100000 + i*1000
                )
                snapshots.append(snapshot)
            
            # 2. 达到涨停
            for i in range(20):  # 涨停持续200秒
                snapshot = self._create_snapshot(
                    stock_code, current_time + timedelta(seconds=100 + i*10),
                    limit_price, 50000 + i*500
                )
                snapshots.append(snapshot)
            
            # 3. 炸板
            break_prices = [
                limit_price * Decimal('0.98'),  # 回落2%
                limit_price * Decimal('0.96'),  # 回落4%
                limit_price * Decimal('0.97'),  # 反弹1%
            ]
            
            for i, price in enumerate(break_prices):
                snapshot = self._create_snapshot(
                    stock_code, current_time + timedelta(seconds=300 + i*10),
                    price, 200000 + i*10000  # 成交量放大
                )
                snapshots.append(snapshot)
        
        elif scenario == "weak_limit_up":
            # 弱势涨停（持续时间短）
            limit_price = base_price * Decimal('1.095')
            
            # 短暂涨停（仅20秒）
            for i in range(2):
                snapshot = self._create_snapshot(
                    stock_code, current_time + timedelta(seconds=i*10),
                    limit_price, 30000
                )
                snapshots.append(snapshot)
            
            # 快速炸板
            snapshot = self._create_snapshot(
                stock_code, current_time + timedelta(seconds=20),
                limit_price * Decimal('0.97'), 100000
            )
            snapshots.append(snapshot)
        
        elif scenario == "strong_limit_up":
            # 强势涨停（持续时间长，成交量大）
            limit_price = base_price * Decimal('1.095')
            
            # 长时间涨停（10分钟）
            for i in range(60):
                snapshot = self._create_snapshot(
                    stock_code, current_time + timedelta(seconds=i*10),
                    limit_price, 500000 + i*1000
                )
                snapshots.append(snapshot)
            
            # 温和炸板
            snapshot = self._create_snapshot(
                stock_code, current_time + timedelta(seconds=600),
                limit_price * Decimal('0.985'), 800000  # 仅回落1.5%
            )
            snapshots.append(snapshot)
        
        return snapshots
    
    def _create_snapshot(self, stock_code: str, timestamp: datetime, price: Decimal, volume: int) -> Level2Snapshot:
        """创建快照数据
        
        Args:
            stock_code: 股票代码
            timestamp: 时间戳
            price: 价格
            volume: 成交量
            
        Returns:
            Level2Snapshot: 快照数据
        """
        return Level2Snapshot(
            stock_code=stock_code,
            timestamp=timestamp,
            last_price=price,
            volume=volume,
            amount=price * volume,
            bid_price_1=price - Decimal('0.01'),
            bid_volume_1=10000,
            ask_price_1=price + Decimal('0.01'),
            ask_volume_1=10000
        )
    
    def test_limit_up_detection(self) -> bool:
        """测试涨停检测功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试涨停检测功能...")
        
        try:
            stock_code = "000001"
            base_price = Decimal('10.00')
            prev_close = base_price
            
            # 设置前收盘价
            self.analyzer.set_prev_close_price(stock_code, prev_close)
            
            # 创建测试数据
            snapshots = self.create_test_snapshots(stock_code, base_price, "normal_limit_up_break")
            
            limit_up_detected = False
            break_detected = False
            
            # 逐个分析快照
            for snapshot in snapshots:
                event = self.analyzer.analyze_snapshot(snapshot)
                
                # 检查涨停状态
                state = self.analyzer.detector.get_limit_up_state(stock_code)
                if state and state.is_limit_up:
                    limit_up_detected = True
                    self.logger.info(f"检测到涨停: {snapshot.timestamp}, 价格: {snapshot.last_price}")
                
                # 检查炸板事件
                if event:
                    break_detected = True
                    self.logger.info(f"检测到炸板事件: 评分={event.score:.2f}, 持续时间={event.duration_seconds}秒")
            
            # 验证结果
            if limit_up_detected and break_detected:
                self.logger.info("涨停检测功能测试成功")
                return True
            else:
                self.logger.error(f"涨停检测功能测试失败: 涨停={limit_up_detected}, 炸板={break_detected}")
                return False
                
        except Exception as e:
            self.logger.error(f"涨停检测功能测试失败: {e}")
            return False
    
    def test_scoring_algorithm(self) -> bool:
        """测试评分算法
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试评分算法...")
        
        try:
            scenarios = [
                ("normal_limit_up_break", "000001", Decimal('10.00')),
                ("weak_limit_up", "000002", Decimal('15.00')),
                ("strong_limit_up", "000003", Decimal('20.00'))
            ]
            
            results = []
            
            for scenario, stock_code, base_price in scenarios:
                # 设置前收盘价
                self.analyzer.set_prev_close_price(stock_code, base_price)
                
                # 创建测试数据
                snapshots = self.create_test_snapshots(stock_code, base_price, scenario)
                
                # 分析快照
                events = []
                for snapshot in snapshots:
                    event = self.analyzer.analyze_snapshot(snapshot)
                    if event:
                        events.append(event)
                
                # 记录结果
                if events:
                    best_event = max(events, key=lambda x: x.score)
                    results.append((scenario, best_event.score))
                    self.logger.info(f"场景 {scenario}: 最高评分 {best_event.score:.2f}")
                else:
                    results.append((scenario, 0.0))
                    self.logger.warning(f"场景 {scenario}: 未检测到炸板事件")
            
            # 验证评分合理性
            # 正常炸板应该得分最高，弱势炸板得分最低
            normal_score = next(score for scenario, score in results if scenario == "normal_limit_up_break")
            weak_score = next(score for scenario, score in results if scenario == "weak_limit_up")
            strong_score = next(score for scenario, score in results if scenario == "strong_limit_up")
            
            if normal_score > weak_score and strong_score > weak_score:
                self.logger.info("评分算法测试成功")
                return True
            else:
                self.logger.error(f"评分算法测试失败: 正常={normal_score:.2f}, 弱势={weak_score:.2f}, 强势={strong_score:.2f}")
                return False
                
        except Exception as e:
            self.logger.error(f"评分算法测试失败: {e}")
            return False
    
    def test_data_management(self) -> bool:
        """测试数据管理功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试数据管理功能...")
        
        try:
            stock_code = "000001"
            base_price = Decimal('10.00')
            
            # 设置前收盘价
            self.analyzer.set_prev_close_price(stock_code, base_price)
            
            # 创建测试数据
            snapshots = self.create_test_snapshots(stock_code, base_price, "normal_limit_up_break")
            
            # 分析数据
            for snapshot in snapshots:
                self.analyzer.analyze_snapshot(snapshot)
            
            # 检查统计信息
            stats = self.analyzer.get_statistics()
            self.logger.info(f"统计信息: {stats}")
            
            # 检查事件获取
            events = self.analyzer.get_break_events(stock_code)
            all_events = self.analyzer.get_all_break_events(min_score=0.0)
            
            self.logger.info(f"股票事件数: {len(events)}, 总事件数: {len(all_events)}")
            
            # 测试数据清理
            cutoff_time = datetime.now() + timedelta(hours=1)
            self.analyzer.cleanup_old_data(cutoff_time)
            
            # 测试重置
            self.analyzer.reset_stock_data(stock_code)
            
            self.logger.info("数据管理功能测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"数据管理功能测试失败: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试
        
        Returns:
            bool: 所有测试是否通过
        """
        self.logger.info("开始涨停炸板分析器完整测试")
        
        tests = [
            ("涨停检测功能测试", self.test_limit_up_detection),
            ("评分算法测试", self.test_scoring_algorithm),
            ("数据管理功能测试", self.test_data_management)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            self.logger.info(f"执行 {test_name}...")
            try:
                result = test_func()
                results.append(result)
                if result:
                    self.logger.info(f"✅ {test_name} 通过")
                else:
                    self.logger.error(f"❌ {test_name} 失败")
            except Exception as e:
                self.logger.error(f"❌ {test_name} 异常: {e}")
                results.append(False)
        
        success_count = sum(results)
        total_count = len(results)
        
        self.logger.info(f"测试完成: {success_count}/{total_count} 通过")
        
        return all(results)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="涨停炸板分析器测试")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--test", "-t", 
                       choices=["detection", "scoring", "management", "all"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = LimitUpAnalyzerTester(args.config)
    
    try:
        if args.test == "detection":
            success = tester.test_limit_up_detection()
        elif args.test == "scoring":
            success = tester.test_scoring_algorithm()
        elif args.test == "management":
            success = tester.test_data_management()
        else:
            success = tester.run_all_tests()
        
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
    sys.exit(main())
