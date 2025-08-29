"""
评分数据模型
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, DateTime, Date, Numeric, Integer, Boolean, Index, Text
from .base import BaseModel


class HistoricalScore(BaseModel):
    """历史评分表"""
    __tablename__ = 'historical_scores'
    
    stock_code = Column(String(10), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    
    # 涨停炸板评分
    limit_up_break_score = Column(Numeric(10, 4), default=0, comment='涨停炸板评分')
    limit_up_break_count = Column(Integer, default=0, comment='涨停炸板次数')
    
    # 跌幅评分
    decline_score = Column(Numeric(10, 4), default=0, comment='跌幅评分')
    decline_rate = Column(Numeric(8, 4), comment='跌幅比例')
    
    # 封单评分
    seal_score = Column(Numeric(10, 4), default=0, comment='封单评分')
    seal_amount = Column(Numeric(15, 2), comment='封单金额')
    
    # 时间评分
    time_score = Column(Numeric(10, 4), default=0, comment='时间评分')
    limit_up_time = Column(DateTime, comment='涨停时间')
    
    # 连续跌幅评分
    continuous_decline_score = Column(Numeric(10, 4), default=0, comment='连续跌幅评分')
    continuous_decline_days = Column(Integer, default=0, comment='连续下跌天数')
    
    # 回封评分
    reseal_score = Column(Numeric(10, 4), default=0, comment='回封评分')
    reseal_count = Column(Integer, default=0, comment='回封次数')
    
    # 总评分
    total_score = Column(Numeric(10, 4), default=0, comment='总评分')
    
    # 评分计算时间
    calculated_at = Column(DateTime, default=datetime.utcnow, comment='计算时间')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_trade_date_score', 'stock_code', 'trade_date'),
        Index('idx_trade_date_score', 'trade_date'),
        Index('idx_total_score', 'total_score'),
        Index('idx_calculated_at', 'calculated_at'),
    )


class StockPoolResult(BaseModel):
    """股票池筛选结果表"""
    __tablename__ = 'stock_pool_results'
    
    stock_code = Column(String(10), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    pool_type = Column(String(10), nullable=False, comment='股票池类型(A/B/ZB)')
    
    # 筛选条件
    market_value = Column(Numeric(20, 2), comment='流通市值(万元)')
    auction_amount = Column(Numeric(15, 2), comment='竞价成交额')
    opening_turnover = Column(Numeric(8, 4), comment='开盘换手率')
    auction_change = Column(Numeric(8, 4), comment='竞价涨幅')
    auction_ratio = Column(Numeric(8, 4), comment='竞价成交比')
    
    # 主力资金分析
    main_fund_net = Column(Numeric(15, 2), comment='主力净额')
    main_fund_ratio = Column(Numeric(8, 4), comment='主力净比')
    large_order_ratio = Column(Numeric(8, 4), comment='大单比例')
    super_large_ratio = Column(Numeric(8, 4), comment='超大单比例')
    
    # 板块分析
    sector_name = Column(String(100), comment='板块名称')
    sector_change = Column(Numeric(8, 4), comment='板块涨幅')
    sector_rank = Column(Integer, comment='板块排名')
    
    # 筛选结果
    is_selected = Column(Boolean, default=False, comment='是否入选')
    selection_reason = Column(Text, comment='入选原因')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_trade_date_pool', 'stock_code', 'trade_date'),
        Index('idx_trade_date_pool', 'trade_date'),
        Index('idx_pool_type', 'pool_type'),
        Index('idx_is_selected', 'is_selected'),
        Index('idx_main_fund_net', 'main_fund_net'),
    )


class TradingSignal(BaseModel):
    """交易信号表"""
    __tablename__ = 'trading_signals'
    
    stock_code = Column(String(10), nullable=False, comment='股票代码')
    signal_time = Column(DateTime, nullable=False, comment='信号时间')
    signal_type = Column(String(20), nullable=False, comment='信号类型')
    strategy_name = Column(String(50), nullable=False, comment='策略名称')
    
    # 信号参数
    trigger_price = Column(Numeric(10, 3), comment='触发价格')
    target_price = Column(Numeric(10, 3), comment='目标价格')
    stop_loss_price = Column(Numeric(10, 3), comment='止损价格')
    position_ratio = Column(Numeric(8, 4), comment='建议仓位比例')
    
    # 市场状态
    current_price = Column(Numeric(10, 3), comment='当前价格')
    volume = Column(Integer, comment='成交量')
    amount = Column(Numeric(15, 2), comment='成交额')
    change_rate = Column(Numeric(8, 4), comment='涨跌幅')
    
    # 主力资金状态
    main_fund_net = Column(Numeric(15, 2), comment='主力净额')
    main_fund_ratio = Column(Numeric(8, 4), comment='主力净比')
    
    # 信号状态
    signal_status = Column(String(20), default='ACTIVE', comment='信号状态')
    confidence = Column(Numeric(5, 4), comment='信号置信度')
    risk_level = Column(String(10), comment='风险等级')
    
    # 执行结果
    executed_at = Column(DateTime, comment='执行时间')
    executed_price = Column(Numeric(10, 3), comment='执行价格')
    executed_volume = Column(Integer, comment='执行数量')
    execution_status = Column(String(20), comment='执行状态')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_signal_time', 'stock_code', 'signal_time'),
        Index('idx_signal_time', 'signal_time'),
        Index('idx_signal_type', 'signal_type'),
        Index('idx_strategy_name', 'strategy_name'),
        Index('idx_signal_status', 'signal_status'),
        Index('idx_confidence', 'confidence'),
    )


class SystemMetrics(BaseModel):
    """系统监控指标表"""
    __tablename__ = 'system_metrics'
    
    metric_time = Column(DateTime, nullable=False, comment='指标时间')
    metric_type = Column(String(50), nullable=False, comment='指标类型')
    metric_name = Column(String(100), nullable=False, comment='指标名称')
    metric_value = Column(Numeric(15, 4), nullable=False, comment='指标值')
    metric_unit = Column(String(20), comment='指标单位')
    
    # 系统信息
    component = Column(String(50), comment='组件名称')
    host_name = Column(String(100), comment='主机名')
    process_id = Column(Integer, comment='进程ID')
    
    # 告警信息
    threshold_value = Column(Numeric(15, 4), comment='阈值')
    is_alert = Column(Boolean, default=False, comment='是否告警')
    alert_level = Column(String(10), comment='告警级别')
    
    # 索引
    __table_args__ = (
        Index('idx_metric_time', 'metric_time'),
        Index('idx_metric_type', 'metric_type'),
        Index('idx_metric_name', 'metric_name'),
        Index('idx_component', 'component'),
        Index('idx_is_alert', 'is_alert'),
    )
