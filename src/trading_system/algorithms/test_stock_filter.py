"""
股票筛选和排序机制测试脚本

测试股票筛选器、排序器和推荐引擎的功能
"""

from datetime import datetime, timedelta
from decimal import Decimal

from ..config import ConfigManager
from ..models.database_init import initialize_database
from .limit_up_break_analyzer import LimitUpBreakEvent
from .stock_filter import (
    create_stock_filter_manager,
    FilterCondition,
    SortCondition,
    FilterOperator,
    SortOrder
)
from ..utils.logger import setup_logger


class StockFilterTester:
    """股票筛选机制测试类"""
    
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
        
        # 筛选管理器配置
        self.filter_config = {
            'filter': {
                'min_score': 30.0,
                'min_price': 1.0,
                'max_price': 1000.0,
                'min_volume': 10000,
                'max_events_age_hours': 24
            },
            'sorter': {},
            'low_risk_threshold': 70.0,
            'medium_risk_threshold': 50.0,
            'high_risk_threshold': 30.0,
            'score_weight': 0.4,
            'volume_weight': 0.3,
            'duration_weight': 0.2,
            'recency_weight': 0.1
        }
        
        # 创建筛选管理器
        self.filter_manager = create_stock_filter_manager(self.filter_config)
        
        self.logger.info("股票筛选机制测试器初始化完成")
    
    def create_test_events(self) -> list:
        """创建测试炸板事件数据
        
        Returns:
            list: 测试事件列表
        """
        events = []
        current_time = datetime.now()
        
        # 高质量炸板事件
        events.append(LimitUpBreakEvent(
            stock_code="000001",
            break_time=current_time - timedelta(hours=1),
            limit_up_price=Decimal('10.95'),
            break_price=Decimal('10.73'),
            break_volume=800000,
            break_amount=Decimal('8584000'),
            duration_seconds=300,
            max_volume_in_window=1000000,
            avg_volume_in_window=500000,
            price_volatility=0.02,
            score=85.5
        ))
        
        # 中等质量炸板事件
        events.append(LimitUpBreakEvent(
            stock_code="000002",
            break_time=current_time - timedelta(hours=3),
            limit_up_price=Decimal('15.68'),
            break_price=Decimal('15.21'),
            break_volume=300000,
            break_amount=Decimal('4563000'),
            duration_seconds=180,
            max_volume_in_window=400000,
            avg_volume_in_window=200000,
            price_volatility=0.04,
            score=62.3
        ))
        
        # 低质量炸板事件
        events.append(LimitUpBreakEvent(
            stock_code="000003",
            break_time=current_time - timedelta(hours=12),
            limit_up_price=Decimal('8.76'),
            break_price=Decimal('8.32'),
            break_volume=50000,
            break_amount=Decimal('416000'),
            duration_seconds=60,
            max_volume_in_window=80000,
            avg_volume_in_window=40000,
            price_volatility=0.08,
            score=35.2
        ))
        
        # 过期事件（超过24小时）
        events.append(LimitUpBreakEvent(
            stock_code="000004",
            break_time=current_time - timedelta(hours=30),
            limit_up_price=Decimal('12.34'),
            break_price=Decimal('11.85'),
            break_volume=600000,
            break_amount=Decimal('7110000'),
            duration_seconds=240,
            max_volume_in_window=700000,
            avg_volume_in_window=350000,
            price_volatility=0.03,
            score=75.8
        ))
        
        # 同一股票的多个事件
        events.append(LimitUpBreakEvent(
            stock_code="000001",
            break_time=current_time - timedelta(hours=2),
            limit_up_price=Decimal('10.95'),
            break_price=Decimal('10.68'),
            break_volume=600000,
            break_amount=Decimal('6408000'),
            duration_seconds=420,
            max_volume_in_window=800000,
            avg_volume_in_window=400000,
            price_volatility=0.025,
            score=78.9
        ))
        
        # 高波动率事件
        events.append(LimitUpBreakEvent(
            stock_code="000005",
            break_time=current_time - timedelta(minutes=30),
            limit_up_price=Decimal('20.45'),
            break_price=Decimal('18.95'),
            break_volume=1200000,
            break_amount=Decimal('22740000'),
            duration_seconds=150,
            max_volume_in_window=1500000,
            avg_volume_in_window=800000,
            price_volatility=0.12,
            score=55.7
        ))
        
        return events
    
    def test_basic_filtering(self) -> bool:
        """测试基本筛选功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试基本筛选功能...")
        
        try:
            # 创建测试数据
            events = self.create_test_events()
            self.logger.info(f"创建测试事件: {len(events)}个")
            
            # 测试默认筛选
            filter_engine = self.filter_manager.recommendation_engine.filter
            filtered_events = filter_engine.apply_filters(events)
            
            self.logger.info(f"默认筛选结果: {len(filtered_events)}个事件")
            
            # 验证筛选结果
            for event in filtered_events:
                # 检查评分阈值
                if event.score < 30.0:
                    self.logger.error(f"筛选失败: 评分过低 {event.score}")
                    return False
                
                # 检查时间阈值
                hours_ago = (datetime.now() - event.break_time).total_seconds() / 3600
                if hours_ago > 24:
                    self.logger.error(f"筛选失败: 事件过期 {hours_ago}小时前")
                    return False
            
            # 测试自定义筛选条件
            custom_filters = [
                FilterCondition('score', FilterOperator.GTE, 60.0, "高评分筛选"),
                FilterCondition('break_volume', FilterOperator.GTE, 500000, "大成交量筛选")
            ]
            
            custom_filtered = filter_engine.apply_filters(events, custom_filters)
            self.logger.info(f"自定义筛选结果: {len(custom_filtered)}个事件")
            
            # 验证自定义筛选
            for event in custom_filtered:
                if event.score < 60.0 or event.break_volume < 500000:
                    self.logger.error(f"自定义筛选失败: 评分={event.score}, 成交量={event.break_volume}")
                    return False
            
            self.logger.info("基本筛选功能测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"基本筛选功能测试失败: {e}")
            return False
    
    def test_sorting_mechanism(self) -> bool:
        """测试排序机制
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试排序机制...")
        
        try:
            # 创建测试数据
            events = self.create_test_events()
            
            # 测试按评分排序
            sorter = self.filter_manager.recommendation_engine.sorter
            score_sorted = sorter.sort_events(events, [
                SortCondition('score', SortOrder.DESC)
            ])
            
            # 验证评分排序
            for i in range(len(score_sorted) - 1):
                if score_sorted[i].score < score_sorted[i + 1].score:
                    self.logger.error(f"评分排序失败: {score_sorted[i].score} < {score_sorted[i + 1].score}")
                    return False
            
            self.logger.info("评分排序测试通过")
            
            # 测试按时间排序
            time_sorted = sorter.sort_events(events, [
                SortCondition('break_time', SortOrder.DESC)
            ])
            
            # 验证时间排序
            for i in range(len(time_sorted) - 1):
                if time_sorted[i].break_time < time_sorted[i + 1].break_time:
                    self.logger.error(f"时间排序失败")
                    return False
            
            self.logger.info("时间排序测试通过")
            
            # 测试多字段排序
            multi_sorted = sorter.sort_events(events, [
                SortCondition('score', SortOrder.DESC, 0.7),
                SortCondition('break_time', SortOrder.DESC, 0.3)
            ])
            
            self.logger.info(f"多字段排序结果: {len(multi_sorted)}个事件")
            
            self.logger.info("排序机制测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"排序机制测试失败: {e}")
            return False
    
    def test_recommendation_engine(self) -> bool:
        """测试推荐引擎
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试推荐引擎...")
        
        try:
            # 创建测试数据
            events = self.create_test_events()
            
            # 生成推荐
            recommendations = self.filter_manager.get_recommendations(
                events, limit=10
            )
            
            self.logger.info(f"生成推荐: {len(recommendations)}个股票")
            
            # 验证推荐结果
            for i, rec in enumerate(recommendations):
                self.logger.info(f"推荐{i+1}: {rec.stock_code}, "
                               f"评分={rec.total_score:.2f}, "
                               f"风险={rec.risk_level}, "
                               f"置信度={rec.confidence:.2f}, "
                               f"理由={rec.recommendation_reason}")
                
                # 验证推荐字段
                if not rec.stock_code:
                    self.logger.error("推荐结果缺少股票代码")
                    return False
                
                if rec.total_score <= 0:
                    self.logger.error("推荐结果评分无效")
                    return False
                
                if rec.risk_level not in ['low', 'medium', 'high']:
                    self.logger.error(f"推荐结果风险等级无效: {rec.risk_level}")
                    return False
                
                if not (0 <= rec.confidence <= 1):
                    self.logger.error(f"推荐结果置信度无效: {rec.confidence}")
                    return False
            
            # 验证排序（评分应该递减）
            for i in range(len(recommendations) - 1):
                if recommendations[i].total_score < recommendations[i + 1].total_score:
                    self.logger.error("推荐结果排序错误")
                    return False
            
            self.logger.info("推荐引擎测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"推荐引擎测试失败: {e}")
            return False
    
    def test_preset_conditions(self) -> bool:
        """测试预设条件
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试预设条件...")
        
        try:
            # 创建测试数据
            events = self.create_test_events()
            
            # 获取可用预设
            presets = self.filter_manager.get_available_presets()
            self.logger.info(f"可用预设: {presets}")
            
            # 测试高质量筛选预设
            high_quality_recs = self.filter_manager.get_recommendations(
                events, filter_preset='high_quality', sort_preset='by_score', limit=5
            )
            
            self.logger.info(f"高质量筛选结果: {len(high_quality_recs)}个推荐")
            
            # 测试最近事件筛选预设
            recent_recs = self.filter_manager.get_recommendations(
                events, filter_preset='recent', sort_preset='by_time', limit=5
            )
            
            self.logger.info(f"最近事件筛选结果: {len(recent_recs)}个推荐")
            
            # 测试活跃交易筛选预设
            active_recs = self.filter_manager.get_recommendations(
                events, filter_preset='active_trading', sort_preset='by_volume', limit=5
            )
            
            self.logger.info(f"活跃交易筛选结果: {len(active_recs)}个推荐")
            
            # 测试综合排序预设
            comprehensive_recs = self.filter_manager.get_recommendations(
                events, sort_preset='comprehensive', limit=5
            )
            
            self.logger.info(f"综合排序结果: {len(comprehensive_recs)}个推荐")
            
            self.logger.info("预设条件测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"预设条件测试失败: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试
        
        Returns:
            bool: 所有测试是否通过
        """
        self.logger.info("开始股票筛选机制完整测试")
        
        tests = [
            ("基本筛选功能测试", self.test_basic_filtering),
            ("排序机制测试", self.test_sorting_mechanism),
            ("推荐引擎测试", self.test_recommendation_engine),
            ("预设条件测试", self.test_preset_conditions)
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
    
    parser = argparse.ArgumentParser(description="股票筛选机制测试")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--test", "-t", 
                       choices=["filtering", "sorting", "recommendation", "presets", "all"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = StockFilterTester(args.config)
    
    try:
        if args.test == "filtering":
            success = tester.test_basic_filtering()
        elif args.test == "sorting":
            success = tester.test_sorting_mechanism()
        elif args.test == "recommendation":
            success = tester.test_recommendation_engine()
        elif args.test == "presets":
            success = tester.test_preset_conditions()
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
