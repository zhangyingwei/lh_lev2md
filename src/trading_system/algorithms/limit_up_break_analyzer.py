"""
涨停炸板分析器

实现涨停炸板识别和评分算法，包括：
- 涨停状态检测
- 炸板事件识别
- 多维度评分计算
- 时间窗口分析
"""

import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

from ..utils.logger import get_logger
from ..utils.exceptions import CalculationException
from ..models import Level2Snapshot, Level2Transaction


@dataclass
class LimitUpBreakEvent:
    """涨停炸板事件"""
    stock_code: str
    break_time: datetime
    limit_up_price: Decimal
    break_price: Decimal
    break_volume: int
    break_amount: Decimal
    duration_seconds: int
    max_volume_in_window: int
    avg_volume_in_window: float
    price_volatility: float
    score: float = 0.0


@dataclass
class LimitUpState:
    """涨停状态"""
    stock_code: str
    is_limit_up: bool = False
    limit_up_price: Decimal = Decimal('0')
    limit_up_start_time: Optional[datetime] = None
    limit_up_duration: int = 0  # 秒
    total_volume_at_limit: int = 0
    total_amount_at_limit: Decimal = Decimal('0')
    max_bid_volume: int = 0
    break_detected: bool = False


class LimitUpBreakDetector:
    """涨停炸板检测器
    
    负责检测股票的涨停状态和炸板事件
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化检测器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('limit_up_detector')
        
        # 涨停检测参数
        self.limit_up_threshold = config.get('limit_up_threshold', 0.095)  # 9.5%涨幅阈值
        self.price_tolerance = config.get('price_tolerance', 0.001)  # 价格容差0.1%
        self.min_limit_duration = config.get('min_limit_duration', 30)  # 最小涨停持续时间30秒
        
        # 炸板检测参数
        self.break_threshold = config.get('break_threshold', 0.02)  # 2%回落阈值
        self.volume_spike_threshold = config.get('volume_spike_threshold', 2.0)  # 成交量激增阈值
        
        # 状态管理
        self.limit_up_states: Dict[str, LimitUpState] = {}
        
        self.logger.info("涨停炸板检测器初始化完成")
    
    def detect_limit_up(self, snapshot: Level2Snapshot, prev_close: Decimal) -> bool:
        """检测涨停状态
        
        Args:
            snapshot: 快照行情数据
            prev_close: 前一日收盘价
            
        Returns:
            bool: 是否处于涨停状态
        """
        try:
            if prev_close <= 0:
                return False
            
            # 计算涨幅
            price_change_rate = float((snapshot.last_price - prev_close) / prev_close)
            
            # 计算理论涨停价
            limit_up_price = prev_close * (1 + Decimal(str(self.limit_up_threshold)))
            
            # 检测是否达到涨停
            price_diff = abs(snapshot.last_price - limit_up_price)
            price_tolerance_amount = limit_up_price * Decimal(str(self.price_tolerance))
            
            is_at_limit = price_diff <= price_tolerance_amount
            
            # 更新涨停状态
            stock_code = snapshot.stock_code
            current_time = snapshot.timestamp
            
            if stock_code not in self.limit_up_states:
                self.limit_up_states[stock_code] = LimitUpState(stock_code=stock_code)
            
            state = self.limit_up_states[stock_code]
            
            if is_at_limit and not state.is_limit_up:
                # 开始涨停
                state.is_limit_up = True
                state.limit_up_price = limit_up_price
                state.limit_up_start_time = current_time
                state.limit_up_duration = 0
                state.total_volume_at_limit = 0
                state.total_amount_at_limit = Decimal('0')
                state.max_bid_volume = snapshot.bid_volume_1
                state.break_detected = False
                
                self.logger.info(f"检测到涨停: {stock_code}, 价格: {snapshot.last_price}, 涨停价: {limit_up_price}")
                
            elif is_at_limit and state.is_limit_up:
                # 持续涨停
                if state.limit_up_start_time:
                    state.limit_up_duration = int((current_time - state.limit_up_start_time).total_seconds())
                
                state.total_volume_at_limit += snapshot.volume
                state.total_amount_at_limit += snapshot.amount
                state.max_bid_volume = max(state.max_bid_volume, snapshot.bid_volume_1)
                
            elif not is_at_limit and state.is_limit_up:
                # 可能的炸板
                if state.limit_up_duration >= self.min_limit_duration:
                    # 满足最小涨停时间，检测炸板
                    break_detected = self._detect_break(snapshot, state, prev_close)
                    if break_detected:
                        state.break_detected = True
                        self.logger.info(f"检测到炸板: {stock_code}, 当前价格: {snapshot.last_price}")
                
                # 重置涨停状态
                state.is_limit_up = False
            
            return state.is_limit_up
            
        except Exception as e:
            self.logger.error(f"涨停检测失败: {e}")
            return False
    
    def _detect_break(self, snapshot: Level2Snapshot, state: LimitUpState, prev_close: Decimal) -> bool:
        """检测炸板事件
        
        Args:
            snapshot: 当前快照数据
            state: 涨停状态
            prev_close: 前一日收盘价
            
        Returns:
            bool: 是否发生炸板
        """
        try:
            # 计算价格回落幅度
            price_drop = float((state.limit_up_price - snapshot.last_price) / state.limit_up_price)
            
            # 检查是否满足炸板条件
            if price_drop >= self.break_threshold:
                return True
            
            # 检查成交量是否异常放大
            if snapshot.volume > 0 and state.total_volume_at_limit > 0:
                volume_ratio = snapshot.volume / (state.total_volume_at_limit / max(1, state.limit_up_duration))
                if volume_ratio >= self.volume_spike_threshold:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"炸板检测失败: {e}")
            return False
    
    def get_limit_up_state(self, stock_code: str) -> Optional[LimitUpState]:
        """获取股票的涨停状态
        
        Args:
            stock_code: 股票代码
            
        Returns:
            LimitUpState: 涨停状态或None
        """
        return self.limit_up_states.get(stock_code)
    
    def reset_state(self, stock_code: str):
        """重置股票状态
        
        Args:
            stock_code: 股票代码
        """
        if stock_code in self.limit_up_states:
            del self.limit_up_states[stock_code]


class LimitUpBreakScorer:
    """涨停炸板评分器
    
    基于多个维度对炸板事件进行评分
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化评分器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('limit_up_scorer')
        
        # 评分权重配置
        self.weights = {
            'duration_weight': config.get('duration_weight', 0.25),      # 涨停持续时间权重
            'volume_weight': config.get('volume_weight', 0.30),          # 成交量权重
            'price_stability_weight': config.get('price_stability_weight', 0.20),  # 价格稳定性权重
            'break_intensity_weight': config.get('break_intensity_weight', 0.25)   # 炸板强度权重
        }
        
        # 评分参数
        self.optimal_duration = config.get('optimal_duration', 300)  # 最佳涨停持续时间5分钟
        self.max_score = config.get('max_score', 100.0)
        
        self.logger.info("涨停炸板评分器初始化完成")
    
    def calculate_score(self, event: LimitUpBreakEvent, market_data: List[Level2Snapshot]) -> float:
        """计算炸板事件评分
        
        Args:
            event: 炸板事件
            market_data: 相关的市场数据
            
        Returns:
            float: 评分结果
        """
        try:
            # 1. 持续时间评分
            duration_score = self._calculate_duration_score(event.duration_seconds)
            
            # 2. 成交量评分
            volume_score = self._calculate_volume_score(event, market_data)
            
            # 3. 价格稳定性评分
            stability_score = self._calculate_price_stability_score(event.price_volatility)
            
            # 4. 炸板强度评分
            intensity_score = self._calculate_break_intensity_score(event)
            
            # 加权计算总分
            total_score = (
                duration_score * self.weights['duration_weight'] +
                volume_score * self.weights['volume_weight'] +
                stability_score * self.weights['price_stability_weight'] +
                intensity_score * self.weights['break_intensity_weight']
            )
            
            # 确保评分在合理范围内
            final_score = min(max(total_score, 0.0), self.max_score)
            
            self.logger.debug(f"炸板评分详情 {event.stock_code}: "
                            f"持续时间={duration_score:.2f}, "
                            f"成交量={volume_score:.2f}, "
                            f"稳定性={stability_score:.2f}, "
                            f"强度={intensity_score:.2f}, "
                            f"总分={final_score:.2f}")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"评分计算失败: {e}")
            return 0.0
    
    def _calculate_duration_score(self, duration_seconds: int) -> float:
        """计算持续时间评分
        
        Args:
            duration_seconds: 持续时间（秒）
            
        Returns:
            float: 持续时间评分
        """
        if duration_seconds <= 0:
            return 0.0
        
        # 使用正态分布函数，最佳持续时间获得最高分
        optimal = self.optimal_duration
        variance = (optimal / 3) ** 2  # 3σ原则
        
        score = math.exp(-((duration_seconds - optimal) ** 2) / (2 * variance))
        return score * self.max_score
    
    def _calculate_volume_score(self, event: LimitUpBreakEvent, market_data: List[Level2Snapshot]) -> float:
        """计算成交量评分
        
        Args:
            event: 炸板事件
            market_data: 市场数据
            
        Returns:
            float: 成交量评分
        """
        try:
            if not market_data or event.avg_volume_in_window <= 0:
                return 0.0
            
            # 计算成交量相对强度
            volume_ratio = event.break_volume / event.avg_volume_in_window
            
            # 使用对数函数，避免极值影响
            if volume_ratio > 1:
                score = min(math.log(volume_ratio) / math.log(10), 1.0)  # 最大为1
            else:
                score = volume_ratio
            
            return score * self.max_score
            
        except Exception as e:
            self.logger.error(f"成交量评分计算失败: {e}")
            return 0.0
    
    def _calculate_price_stability_score(self, volatility: float) -> float:
        """计算价格稳定性评分
        
        Args:
            volatility: 价格波动率
            
        Returns:
            float: 稳定性评分
        """
        if volatility <= 0:
            return self.max_score
        
        # 波动率越低，稳定性评分越高
        stability_score = max(0.0, 1.0 - volatility * 10)  # 假设10%波动率对应0分
        return stability_score * self.max_score
    
    def _calculate_break_intensity_score(self, event: LimitUpBreakEvent) -> float:
        """计算炸板强度评分
        
        Args:
            event: 炸板事件
            
        Returns:
            float: 强度评分
        """
        try:
            # 计算价格回落幅度
            price_drop_rate = float((event.limit_up_price - event.break_price) / event.limit_up_price)
            
            # 适中的回落幅度获得较高评分（2-5%为最佳）
            if 0.02 <= price_drop_rate <= 0.05:
                intensity_score = 1.0
            elif price_drop_rate < 0.02:
                intensity_score = price_drop_rate / 0.02
            else:
                intensity_score = max(0.0, 1.0 - (price_drop_rate - 0.05) / 0.05)
            
            return intensity_score * self.max_score
            
        except Exception as e:
            self.logger.error(f"炸板强度评分计算失败: {e}")
            return 0.0


class LimitUpBreakAnalyzer:
    """涨停炸板分析器

    集成检测器和评分器，提供完整的涨停炸板分析功能
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化分析器

        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('limit_up_analyzer')

        # 创建检测器和评分器
        self.detector = LimitUpBreakDetector(config.get('detector', {}))
        self.scorer = LimitUpBreakScorer(config.get('scorer', {}))

        # 数据窗口管理
        self.window_size = config.get('window_size', 300)  # 5分钟窗口
        self.market_data_windows: Dict[str, deque] = {}

        # 炸板事件缓存
        self.break_events: Dict[str, List[LimitUpBreakEvent]] = {}
        self.max_events_per_stock = config.get('max_events_per_stock', 10)

        # 前收盘价缓存
        self.prev_close_prices: Dict[str, Decimal] = {}

        self.logger.info("涨停炸板分析器初始化完成")

    def set_prev_close_price(self, stock_code: str, prev_close: Decimal):
        """设置股票的前收盘价

        Args:
            stock_code: 股票代码
            prev_close: 前收盘价
        """
        self.prev_close_prices[stock_code] = prev_close

    def analyze_snapshot(self, snapshot: Level2Snapshot) -> Optional[LimitUpBreakEvent]:
        """分析快照数据，检测涨停炸板事件

        Args:
            snapshot: 快照行情数据

        Returns:
            LimitUpBreakEvent: 炸板事件或None
        """
        try:
            stock_code = snapshot.stock_code

            # 获取前收盘价
            prev_close = self.prev_close_prices.get(stock_code)
            if not prev_close:
                self.logger.warning(f"缺少前收盘价: {stock_code}")
                return None

            # 更新数据窗口
            self._update_data_window(snapshot)

            # 检测涨停状态
            is_limit_up = self.detector.detect_limit_up(snapshot, prev_close)

            # 获取当前状态
            state = self.detector.get_limit_up_state(stock_code)
            if not state:
                return None

            # 检查是否发生炸板
            if state.break_detected and not state.is_limit_up:
                # 创建炸板事件
                event = self._create_break_event(snapshot, state, prev_close)
                if event:
                    # 计算评分
                    market_data = list(self.market_data_windows.get(stock_code, []))
                    event.score = self.scorer.calculate_score(event, market_data)

                    # 缓存事件
                    self._cache_break_event(event)

                    self.logger.info(f"炸板事件: {stock_code}, 评分: {event.score:.2f}")
                    return event

            return None

        except Exception as e:
            self.logger.error(f"快照分析失败: {e}")
            return None

    def _update_data_window(self, snapshot: Level2Snapshot):
        """更新数据窗口

        Args:
            snapshot: 快照数据
        """
        stock_code = snapshot.stock_code
        current_time = snapshot.timestamp

        # 初始化窗口
        if stock_code not in self.market_data_windows:
            self.market_data_windows[stock_code] = deque(maxlen=self.window_size)

        window = self.market_data_windows[stock_code]

        # 添加新数据
        window.append(snapshot)

        # 清理过期数据
        cutoff_time = current_time - timedelta(seconds=self.window_size)
        while window and window[0].timestamp < cutoff_time:
            window.popleft()

    def _create_break_event(self, snapshot: Level2Snapshot, state: LimitUpState, prev_close: Decimal) -> Optional[LimitUpBreakEvent]:
        """创建炸板事件

        Args:
            snapshot: 当前快照
            state: 涨停状态
            prev_close: 前收盘价

        Returns:
            LimitUpBreakEvent: 炸板事件或None
        """
        try:
            stock_code = snapshot.stock_code
            window = self.market_data_windows.get(stock_code, deque())

            if not window:
                return None

            # 计算窗口内统计数据
            volumes = [s.volume for s in window if s.volume > 0]
            max_volume = max(volumes) if volumes else 0
            avg_volume = sum(volumes) / len(volumes) if volumes else 0

            # 计算价格波动率
            prices = [float(s.last_price) for s in window]
            if len(prices) > 1:
                price_volatility = self._calculate_volatility(prices)
            else:
                price_volatility = 0.0

            # 创建事件
            event = LimitUpBreakEvent(
                stock_code=stock_code,
                break_time=snapshot.timestamp,
                limit_up_price=state.limit_up_price,
                break_price=snapshot.last_price,
                break_volume=snapshot.volume,
                break_amount=snapshot.amount,
                duration_seconds=state.limit_up_duration,
                max_volume_in_window=max_volume,
                avg_volume_in_window=avg_volume,
                price_volatility=price_volatility
            )

            return event

        except Exception as e:
            self.logger.error(f"创建炸板事件失败: {e}")
            return None

    def _calculate_volatility(self, prices: List[float]) -> float:
        """计算价格波动率

        Args:
            prices: 价格列表

        Returns:
            float: 波动率
        """
        if len(prices) < 2:
            return 0.0

        # 计算收益率
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if not returns:
            return 0.0

        # 计算标准差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance)

        return volatility

    def _cache_break_event(self, event: LimitUpBreakEvent):
        """缓存炸板事件

        Args:
            event: 炸板事件
        """
        stock_code = event.stock_code

        if stock_code not in self.break_events:
            self.break_events[stock_code] = []

        events = self.break_events[stock_code]
        events.append(event)

        # 保持事件数量限制
        if len(events) > self.max_events_per_stock:
            events.pop(0)

    def get_break_events(self, stock_code: str, limit: int = 10) -> List[LimitUpBreakEvent]:
        """获取股票的炸板事件

        Args:
            stock_code: 股票代码
            limit: 返回数量限制

        Returns:
            List[LimitUpBreakEvent]: 炸板事件列表
        """
        events = self.break_events.get(stock_code, [])
        return sorted(events, key=lambda x: x.break_time, reverse=True)[:limit]

    def get_all_break_events(self, min_score: float = 0.0, limit: int = 100) -> List[LimitUpBreakEvent]:
        """获取所有炸板事件

        Args:
            min_score: 最小评分阈值
            limit: 返回数量限制

        Returns:
            List[LimitUpBreakEvent]: 炸板事件列表
        """
        all_events = []
        for events in self.break_events.values():
            all_events.extend(events)

        # 过滤和排序
        filtered_events = [e for e in all_events if e.score >= min_score]
        sorted_events = sorted(filtered_events, key=lambda x: x.score, reverse=True)

        return sorted_events[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息

        Returns:
            Dict: 统计信息
        """
        total_events = sum(len(events) for events in self.break_events.values())

        if total_events > 0:
            all_scores = []
            for events in self.break_events.values():
                all_scores.extend([e.score for e in events])

            avg_score = sum(all_scores) / len(all_scores)
            max_score = max(all_scores)
            min_score = min(all_scores)
        else:
            avg_score = max_score = min_score = 0.0

        return {
            'total_stocks': len(self.break_events),
            'total_events': total_events,
            'avg_score': avg_score,
            'max_score': max_score,
            'min_score': min_score,
            'window_size': self.window_size,
            'cached_prev_close_count': len(self.prev_close_prices)
        }

    def reset_stock_data(self, stock_code: str):
        """重置股票数据

        Args:
            stock_code: 股票代码
        """
        # 清理检测器状态
        self.detector.reset_state(stock_code)

        # 清理数据窗口
        if stock_code in self.market_data_windows:
            del self.market_data_windows[stock_code]

        # 清理事件缓存
        if stock_code in self.break_events:
            del self.break_events[stock_code]

    def cleanup_old_data(self, cutoff_time: datetime):
        """清理过期数据

        Args:
            cutoff_time: 截止时间
        """
        # 清理过期事件
        for stock_code, events in list(self.break_events.items()):
            self.break_events[stock_code] = [
                e for e in events if e.break_time >= cutoff_time
            ]

            # 如果没有事件了，删除整个条目
            if not self.break_events[stock_code]:
                del self.break_events[stock_code]


def create_limit_up_analyzer(config: Dict[str, Any]) -> LimitUpBreakAnalyzer:
    """创建涨停炸板分析器

    Args:
        config: 配置参数

    Returns:
        LimitUpBreakAnalyzer: 分析器实例
    """
    return LimitUpBreakAnalyzer(config)
