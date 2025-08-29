"""
股票筛选和排序机制

实现基于评分的股票筛选、排序和推荐机制，支持多维度筛选条件
包括价格筛选、成交量筛选、评分筛选、时间筛选等功能
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import get_logger
from ..utils.exceptions import ValidationException
from ..models import Level2Snapshot
from .limit_up_break_analyzer import LimitUpBreakEvent


class SortOrder(Enum):
    """排序方向"""
    ASC = "asc"   # 升序
    DESC = "desc" # 降序


class FilterOperator(Enum):
    """筛选操作符"""
    EQ = "eq"     # 等于
    NE = "ne"     # 不等于
    GT = "gt"     # 大于
    GTE = "gte"   # 大于等于
    LT = "lt"     # 小于
    LTE = "lte"   # 小于等于
    IN = "in"     # 包含
    NOT_IN = "not_in"  # 不包含
    BETWEEN = "between"  # 区间


@dataclass
class FilterCondition:
    """筛选条件"""
    field: str                    # 字段名
    operator: FilterOperator      # 操作符
    value: Union[Any, List[Any]]  # 值或值列表
    description: str = ""         # 条件描述


@dataclass
class SortCondition:
    """排序条件"""
    field: str           # 排序字段
    order: SortOrder     # 排序方向
    weight: float = 1.0  # 权重（用于多字段排序）


@dataclass
class StockRecommendation:
    """股票推荐结果"""
    stock_code: str
    stock_name: str = ""
    current_price: Decimal = Decimal('0')
    break_events: List[LimitUpBreakEvent] = None
    total_score: float = 0.0
    rank: int = 0
    recommendation_reason: str = ""
    risk_level: str = "medium"
    confidence: float = 0.0


class StockFilter:
    """股票筛选器
    
    提供灵活的股票筛选功能，支持多种筛选条件组合
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化筛选器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('stock_filter')
        
        # 默认筛选条件
        self.default_filters = {
            'min_score': config.get('min_score', 30.0),
            'min_price': config.get('min_price', 1.0),
            'max_price': config.get('max_price', 1000.0),
            'min_volume': config.get('min_volume', 10000),
            'max_events_age_hours': config.get('max_events_age_hours', 24)
        }
        
        self.logger.info("股票筛选器初始化完成")
    
    def apply_filters(self, 
                     events: List[LimitUpBreakEvent], 
                     conditions: List[FilterCondition] = None) -> List[LimitUpBreakEvent]:
        """应用筛选条件
        
        Args:
            events: 炸板事件列表
            conditions: 筛选条件列表
            
        Returns:
            List[LimitUpBreakEvent]: 筛选后的事件列表
        """
        try:
            if not events:
                return []
            
            filtered_events = events.copy()
            
            # 应用默认筛选条件
            filtered_events = self._apply_default_filters(filtered_events)
            
            # 应用自定义筛选条件
            if conditions:
                for condition in conditions:
                    filtered_events = self._apply_single_filter(filtered_events, condition)
            
            self.logger.info(f"筛选完成: {len(events)} -> {len(filtered_events)}")
            return filtered_events
            
        except Exception as e:
            self.logger.error(f"筛选失败: {e}")
            return []
    
    def _apply_default_filters(self, events: List[LimitUpBreakEvent]) -> List[LimitUpBreakEvent]:
        """应用默认筛选条件
        
        Args:
            events: 事件列表
            
        Returns:
            List[LimitUpBreakEvent]: 筛选后的事件列表
        """
        filtered = []
        current_time = datetime.now()
        max_age = timedelta(hours=self.default_filters['max_events_age_hours'])
        
        for event in events:
            # 评分筛选
            if event.score < self.default_filters['min_score']:
                continue
            
            # 价格筛选
            if (event.break_price < self.default_filters['min_price'] or 
                event.break_price > self.default_filters['max_price']):
                continue
            
            # 成交量筛选
            if event.break_volume < self.default_filters['min_volume']:
                continue
            
            # 时间筛选
            if current_time - event.break_time > max_age:
                continue
            
            filtered.append(event)
        
        return filtered
    
    def _apply_single_filter(self, 
                           events: List[LimitUpBreakEvent], 
                           condition: FilterCondition) -> List[LimitUpBreakEvent]:
        """应用单个筛选条件
        
        Args:
            events: 事件列表
            condition: 筛选条件
            
        Returns:
            List[LimitUpBreakEvent]: 筛选后的事件列表
        """
        try:
            filtered = []
            
            for event in events:
                # 获取字段值
                field_value = self._get_field_value(event, condition.field)
                if field_value is None:
                    continue
                
                # 应用操作符
                if self._evaluate_condition(field_value, condition.operator, condition.value):
                    filtered.append(event)
            
            return filtered
            
        except Exception as e:
            self.logger.error(f"应用筛选条件失败: {e}")
            return events
    
    def _get_field_value(self, event: LimitUpBreakEvent, field: str) -> Any:
        """获取事件字段值
        
        Args:
            event: 炸板事件
            field: 字段名
            
        Returns:
            Any: 字段值
        """
        field_mapping = {
            'stock_code': event.stock_code,
            'score': event.score,
            'break_price': float(event.break_price),
            'limit_up_price': float(event.limit_up_price),
            'break_volume': event.break_volume,
            'break_amount': float(event.break_amount),
            'duration_seconds': event.duration_seconds,
            'max_volume_in_window': event.max_volume_in_window,
            'avg_volume_in_window': event.avg_volume_in_window,
            'price_volatility': event.price_volatility,
            'break_time': event.break_time,
            'price_drop_rate': float((event.limit_up_price - event.break_price) / event.limit_up_price)
        }
        
        return field_mapping.get(field)
    
    def _evaluate_condition(self, field_value: Any, operator: FilterOperator, target_value: Any) -> bool:
        """评估筛选条件
        
        Args:
            field_value: 字段值
            operator: 操作符
            target_value: 目标值
            
        Returns:
            bool: 是否满足条件
        """
        try:
            if operator == FilterOperator.EQ:
                return field_value == target_value
            elif operator == FilterOperator.NE:
                return field_value != target_value
            elif operator == FilterOperator.GT:
                return field_value > target_value
            elif operator == FilterOperator.GTE:
                return field_value >= target_value
            elif operator == FilterOperator.LT:
                return field_value < target_value
            elif operator == FilterOperator.LTE:
                return field_value <= target_value
            elif operator == FilterOperator.IN:
                return field_value in target_value
            elif operator == FilterOperator.NOT_IN:
                return field_value not in target_value
            elif operator == FilterOperator.BETWEEN:
                if isinstance(target_value, (list, tuple)) and len(target_value) == 2:
                    return target_value[0] <= field_value <= target_value[1]
                return False
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"条件评估失败: {e}")
            return False


class StockSorter:
    """股票排序器
    
    提供多维度的股票排序功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化排序器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('stock_sorter')
        
        # 默认排序配置
        self.default_sort = [
            SortCondition('score', SortOrder.DESC, 0.6),      # 评分权重60%
            SortCondition('break_time', SortOrder.DESC, 0.2), # 时间权重20%
            SortCondition('break_volume', SortOrder.DESC, 0.2) # 成交量权重20%
        ]
        
        self.logger.info("股票排序器初始化完成")
    
    def sort_events(self, 
                   events: List[LimitUpBreakEvent], 
                   sort_conditions: List[SortCondition] = None) -> List[LimitUpBreakEvent]:
        """排序炸板事件
        
        Args:
            events: 事件列表
            sort_conditions: 排序条件列表
            
        Returns:
            List[LimitUpBreakEvent]: 排序后的事件列表
        """
        try:
            if not events:
                return []
            
            conditions = sort_conditions or self.default_sort
            
            # 多字段排序
            sorted_events = sorted(events, key=lambda event: self._get_sort_key(event, conditions))
            
            self.logger.info(f"排序完成: {len(sorted_events)}个事件")
            return sorted_events
            
        except Exception as e:
            self.logger.error(f"排序失败: {e}")
            return events
    
    def _get_sort_key(self, event: LimitUpBreakEvent, conditions: List[SortCondition]) -> tuple:
        """获取排序键
        
        Args:
            event: 炸板事件
            conditions: 排序条件
            
        Returns:
            tuple: 排序键
        """
        sort_values = []
        
        for condition in conditions:
            # 获取字段值
            field_value = self._get_field_value(event, condition.field)
            
            # 处理排序方向
            if condition.order == SortOrder.DESC:
                if isinstance(field_value, (int, float)):
                    field_value = -field_value
                elif isinstance(field_value, datetime):
                    field_value = -field_value.timestamp()
                elif isinstance(field_value, str):
                    # 字符串反向排序比较复杂，这里简化处理
                    pass
            
            sort_values.append(field_value)
        
        return tuple(sort_values)
    
    def _get_field_value(self, event: LimitUpBreakEvent, field: str) -> Any:
        """获取事件字段值（与筛选器相同的逻辑）"""
        field_mapping = {
            'stock_code': event.stock_code,
            'score': event.score,
            'break_price': float(event.break_price),
            'limit_up_price': float(event.limit_up_price),
            'break_volume': event.break_volume,
            'break_amount': float(event.break_amount),
            'duration_seconds': event.duration_seconds,
            'max_volume_in_window': event.max_volume_in_window,
            'avg_volume_in_window': event.avg_volume_in_window,
            'price_volatility': event.price_volatility,
            'break_time': event.break_time
        }
        
        return field_mapping.get(field, 0)


class StockRecommendationEngine:
    """股票推荐引擎

    基于炸板事件分析生成股票推荐
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化推荐引擎

        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('stock_recommender')

        # 创建筛选器和排序器
        self.filter = StockFilter(config.get('filter', {}))
        self.sorter = StockSorter(config.get('sorter', {}))

        # 推荐配置
        self.risk_thresholds = {
            'low': config.get('low_risk_threshold', 70.0),
            'medium': config.get('medium_risk_threshold', 50.0),
            'high': config.get('high_risk_threshold', 30.0)
        }

        self.confidence_weights = {
            'score_weight': config.get('score_weight', 0.4),
            'volume_weight': config.get('volume_weight', 0.3),
            'duration_weight': config.get('duration_weight', 0.2),
            'recency_weight': config.get('recency_weight', 0.1)
        }

        self.logger.info("股票推荐引擎初始化完成")

    def generate_recommendations(self,
                               events: List[LimitUpBreakEvent],
                               filter_conditions: List[FilterCondition] = None,
                               sort_conditions: List[SortCondition] = None,
                               limit: int = 20) -> List[StockRecommendation]:
        """生成股票推荐

        Args:
            events: 炸板事件列表
            filter_conditions: 筛选条件
            sort_conditions: 排序条件
            limit: 推荐数量限制

        Returns:
            List[StockRecommendation]: 推荐结果列表
        """
        try:
            # 1. 筛选事件
            filtered_events = self.filter.apply_filters(events, filter_conditions)

            # 2. 排序事件
            sorted_events = self.sorter.sort_events(filtered_events, sort_conditions)

            # 3. 按股票分组
            stock_events = self._group_events_by_stock(sorted_events)

            # 4. 生成推荐
            recommendations = []
            for stock_code, stock_events_list in stock_events.items():
                recommendation = self._create_recommendation(stock_code, stock_events_list)
                if recommendation:
                    recommendations.append(recommendation)

            # 5. 排序推荐结果
            recommendations.sort(key=lambda x: x.total_score, reverse=True)

            # 6. 设置排名
            for i, rec in enumerate(recommendations[:limit]):
                rec.rank = i + 1

            self.logger.info(f"生成推荐完成: {len(recommendations)}个股票")
            return recommendations[:limit]

        except Exception as e:
            self.logger.error(f"生成推荐失败: {e}")
            return []

    def _group_events_by_stock(self, events: List[LimitUpBreakEvent]) -> Dict[str, List[LimitUpBreakEvent]]:
        """按股票分组事件

        Args:
            events: 事件列表

        Returns:
            Dict: 按股票代码分组的事件字典
        """
        stock_events = {}
        for event in events:
            if event.stock_code not in stock_events:
                stock_events[event.stock_code] = []
            stock_events[event.stock_code].append(event)

        return stock_events

    def _create_recommendation(self, stock_code: str, events: List[LimitUpBreakEvent]) -> Optional[StockRecommendation]:
        """创建股票推荐

        Args:
            stock_code: 股票代码
            events: 该股票的事件列表

        Returns:
            StockRecommendation: 推荐结果或None
        """
        try:
            if not events:
                return None

            # 计算综合评分
            total_score = self._calculate_total_score(events)

            # 确定风险等级
            risk_level = self._determine_risk_level(total_score, events)

            # 计算置信度
            confidence = self._calculate_confidence(events)

            # 生成推荐理由
            reason = self._generate_recommendation_reason(events)

            # 获取最新价格
            latest_event = max(events, key=lambda x: x.break_time)

            recommendation = StockRecommendation(
                stock_code=stock_code,
                current_price=latest_event.break_price,
                break_events=events,
                total_score=total_score,
                recommendation_reason=reason,
                risk_level=risk_level,
                confidence=confidence
            )

            return recommendation

        except Exception as e:
            self.logger.error(f"创建推荐失败: {e}")
            return None

    def _calculate_total_score(self, events: List[LimitUpBreakEvent]) -> float:
        """计算综合评分

        Args:
            events: 事件列表

        Returns:
            float: 综合评分
        """
        if not events:
            return 0.0

        # 使用最高评分和平均评分的加权平均
        scores = [event.score for event in events]
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)

        # 最高评分权重70%，平均评分权重30%
        total_score = max_score * 0.7 + avg_score * 0.3

        # 考虑事件数量加成（多次炸板可能表示更强的关注度）
        event_count_bonus = min(len(events) * 2, 10)  # 最多10分加成

        return min(total_score + event_count_bonus, 100.0)

    def _determine_risk_level(self, total_score: float, events: List[LimitUpBreakEvent]) -> str:
        """确定风险等级

        Args:
            total_score: 综合评分
            events: 事件列表

        Returns:
            str: 风险等级
        """
        # 基于评分的基础风险等级
        if total_score >= self.risk_thresholds['low']:
            base_risk = 'low'
        elif total_score >= self.risk_thresholds['medium']:
            base_risk = 'medium'
        else:
            base_risk = 'high'

        # 考虑其他因素调整风险等级
        latest_event = max(events, key=lambda x: x.break_time)

        # 如果价格波动率过高，提升风险等级
        if latest_event.price_volatility > 0.05:  # 5%波动率
            if base_risk == 'low':
                base_risk = 'medium'
            elif base_risk == 'medium':
                base_risk = 'high'

        # 如果炸板幅度过大，提升风险等级
        price_drop = float((latest_event.limit_up_price - latest_event.break_price) / latest_event.limit_up_price)
        if price_drop > 0.08:  # 回落超过8%
            if base_risk == 'low':
                base_risk = 'medium'

        return base_risk

    def _calculate_confidence(self, events: List[LimitUpBreakEvent]) -> float:
        """计算置信度

        Args:
            events: 事件列表

        Returns:
            float: 置信度 (0-1)
        """
        if not events:
            return 0.0

        latest_event = max(events, key=lambda x: x.break_time)

        # 评分因子
        score_factor = min(latest_event.score / 100.0, 1.0)

        # 成交量因子
        volume_factor = min(latest_event.break_volume / 1000000, 1.0)  # 100万成交量为满分

        # 持续时间因子
        duration_factor = min(latest_event.duration_seconds / 600, 1.0)  # 10分钟为满分

        # 时效性因子
        hours_ago = (datetime.now() - latest_event.break_time).total_seconds() / 3600
        recency_factor = max(0.0, 1.0 - hours_ago / 24)  # 24小时内线性衰减

        # 加权计算置信度
        confidence = (
            score_factor * self.confidence_weights['score_weight'] +
            volume_factor * self.confidence_weights['volume_weight'] +
            duration_factor * self.confidence_weights['duration_weight'] +
            recency_factor * self.confidence_weights['recency_weight']
        )

        return min(max(confidence, 0.0), 1.0)

    def _generate_recommendation_reason(self, events: List[LimitUpBreakEvent]) -> str:
        """生成推荐理由

        Args:
            events: 事件列表

        Returns:
            str: 推荐理由
        """
        if not events:
            return "无有效数据"

        latest_event = max(events, key=lambda x: x.break_time)
        reasons = []

        # 评分相关
        if latest_event.score >= 80:
            reasons.append("高质量炸板信号")
        elif latest_event.score >= 60:
            reasons.append("良好炸板信号")

        # 持续时间相关
        if latest_event.duration_seconds >= 300:  # 5分钟以上
            reasons.append("涨停持续时间较长")

        # 成交量相关
        if latest_event.break_volume >= 500000:  # 50万以上
            reasons.append("炸板成交量活跃")

        # 多次炸板
        if len(events) > 1:
            reasons.append(f"近期{len(events)}次炸板事件")

        # 时效性
        hours_ago = (datetime.now() - latest_event.break_time).total_seconds() / 3600
        if hours_ago < 1:
            reasons.append("最新炸板信号")
        elif hours_ago < 6:
            reasons.append("近期炸板信号")

        return "; ".join(reasons) if reasons else "基于炸板分析"


class StockFilterManager:
    """股票筛选管理器

    集成筛选、排序和推荐功能的统一管理器
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化管理器

        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('stock_filter_manager')

        # 创建推荐引擎
        self.recommendation_engine = StockRecommendationEngine(config)

        # 预定义筛选条件
        self.predefined_filters = self._create_predefined_filters()

        # 预定义排序条件
        self.predefined_sorts = self._create_predefined_sorts()

        self.logger.info("股票筛选管理器初始化完成")

    def _create_predefined_filters(self) -> Dict[str, List[FilterCondition]]:
        """创建预定义筛选条件

        Returns:
            Dict: 预定义筛选条件字典
        """
        return {
            'high_quality': [
                FilterCondition('score', FilterOperator.GTE, 70.0, "高质量炸板"),
                FilterCondition('duration_seconds', FilterOperator.GTE, 180, "涨停持续3分钟以上"),
                FilterCondition('break_volume', FilterOperator.GTE, 100000, "成交量10万以上")
            ],
            'recent': [
                FilterCondition('break_time', FilterOperator.GTE,
                              datetime.now() - timedelta(hours=6), "6小时内炸板")
            ],
            'active_trading': [
                FilterCondition('break_volume', FilterOperator.GTE, 500000, "成交量50万以上"),
                FilterCondition('avg_volume_in_window', FilterOperator.GTE, 100000, "平均成交量活跃")
            ],
            'stable_price': [
                FilterCondition('price_volatility', FilterOperator.LTE, 0.03, "价格波动率3%以下"),
                FilterCondition('price_drop_rate', FilterOperator.LTE, 0.05, "回落幅度5%以下")
            ]
        }

    def _create_predefined_sorts(self) -> Dict[str, List[SortCondition]]:
        """创建预定义排序条件

        Returns:
            Dict: 预定义排序条件字典
        """
        return {
            'by_score': [
                SortCondition('score', SortOrder.DESC, 1.0)
            ],
            'by_time': [
                SortCondition('break_time', SortOrder.DESC, 1.0)
            ],
            'by_volume': [
                SortCondition('break_volume', SortOrder.DESC, 1.0)
            ],
            'comprehensive': [
                SortCondition('score', SortOrder.DESC, 0.5),
                SortCondition('break_time', SortOrder.DESC, 0.3),
                SortCondition('break_volume', SortOrder.DESC, 0.2)
            ]
        }

    def get_recommendations(self,
                          events: List[LimitUpBreakEvent],
                          filter_preset: str = None,
                          sort_preset: str = None,
                          custom_filters: List[FilterCondition] = None,
                          custom_sorts: List[SortCondition] = None,
                          limit: int = 20) -> List[StockRecommendation]:
        """获取股票推荐

        Args:
            events: 炸板事件列表
            filter_preset: 预定义筛选条件名称
            sort_preset: 预定义排序条件名称
            custom_filters: 自定义筛选条件
            custom_sorts: 自定义排序条件
            limit: 推荐数量限制

        Returns:
            List[StockRecommendation]: 推荐结果列表
        """
        try:
            # 确定筛选条件
            filter_conditions = custom_filters
            if filter_preset and filter_preset in self.predefined_filters:
                preset_filters = self.predefined_filters[filter_preset]
                if filter_conditions:
                    filter_conditions.extend(preset_filters)
                else:
                    filter_conditions = preset_filters

            # 确定排序条件
            sort_conditions = custom_sorts
            if sort_preset and sort_preset in self.predefined_sorts:
                sort_conditions = self.predefined_sorts[sort_preset]

            # 生成推荐
            recommendations = self.recommendation_engine.generate_recommendations(
                events, filter_conditions, sort_conditions, limit
            )

            self.logger.info(f"获取推荐完成: {len(recommendations)}个推荐")
            return recommendations

        except Exception as e:
            self.logger.error(f"获取推荐失败: {e}")
            return []

    def get_available_presets(self) -> Dict[str, Dict[str, List[str]]]:
        """获取可用的预设条件

        Returns:
            Dict: 预设条件字典
        """
        return {
            'filters': {
                'names': list(self.predefined_filters.keys()),
                'descriptions': {
                    'high_quality': '高质量炸板筛选',
                    'recent': '最近炸板筛选',
                    'active_trading': '活跃交易筛选',
                    'stable_price': '价格稳定筛选'
                }
            },
            'sorts': {
                'names': list(self.predefined_sorts.keys()),
                'descriptions': {
                    'by_score': '按评分排序',
                    'by_time': '按时间排序',
                    'by_volume': '按成交量排序',
                    'comprehensive': '综合排序'
                }
            }
        }


def create_stock_filter_manager(config: Dict[str, Any]) -> StockFilterManager:
    """创建股票筛选管理器

    Args:
        config: 配置参数

    Returns:
        StockFilterManager: 管理器实例
    """
    return StockFilterManager(config)
