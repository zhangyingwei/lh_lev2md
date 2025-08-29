"""
股票数据模型
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, String, DateTime, Date, Numeric, Integer, Boolean, Index, Text
from .base import BaseModel


class StockInfo(BaseModel):
    """股票基础信息表"""
    __tablename__ = 'stock_info'
    
    stock_code = Column(String(10), unique=True, nullable=False, comment='股票代码')
    stock_name = Column(String(100), nullable=False, comment='股票名称')
    market = Column(String(10), nullable=False, comment='市场(SH/SZ)')
    industry = Column(String(100), comment='所属行业')
    concept = Column(Text, comment='概念板块(JSON格式)')
    list_date = Column(Date, comment='上市日期')
    total_shares = Column(Numeric(20, 2), comment='总股本(万股)')
    float_shares = Column(Numeric(20, 2), comment='流通股本(万股)')
    market_value = Column(Numeric(20, 2), comment='总市值(万元)')
    float_market_value = Column(Numeric(20, 2), comment='流通市值(万元)')
    is_active = Column(Boolean, default=True, comment='是否活跃')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_code', 'stock_code'),
        Index('idx_stock_name', 'stock_name'),
        Index('idx_market', 'market'),
        Index('idx_float_market_value', 'float_market_value'),
        Index('idx_is_active', 'is_active'),
    )


class DailyQuote(BaseModel):
    """日线行情表"""
    __tablename__ = 'daily_quote'
    
    stock_code = Column(String(10), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    pre_close = Column(Numeric(10, 3), nullable=False, comment='前收盘价')
    open_price = Column(Numeric(10, 3), nullable=False, comment='开盘价')
    high_price = Column(Numeric(10, 3), nullable=False, comment='最高价')
    low_price = Column(Numeric(10, 3), nullable=False, comment='最低价')
    close_price = Column(Numeric(10, 3), nullable=False, comment='收盘价')
    volume = Column(Integer, nullable=False, comment='成交量(股)')
    amount = Column(Numeric(15, 2), nullable=False, comment='成交额(元)')
    turnover_rate = Column(Numeric(8, 4), comment='换手率(%)')
    change_amount = Column(Numeric(10, 3), comment='涨跌额')
    change_rate = Column(Numeric(8, 4), comment='涨跌幅(%)')
    amplitude = Column(Numeric(8, 4), comment='振幅(%)')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_trade_date', 'stock_code', 'trade_date'),
        Index('idx_trade_date', 'trade_date'),
        Index('idx_change_rate', 'change_rate'),
        Index('idx_turnover_rate', 'turnover_rate'),
    )


class Level2Snapshot(BaseModel):
    """Level2快照行情表"""
    __tablename__ = 'level2_snapshots'
    
    stock_code = Column(String(10), nullable=False, comment='股票代码')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    last_price = Column(Numeric(10, 3), nullable=False, comment='最新价')
    volume = Column(Integer, nullable=False, comment='成交量')
    amount = Column(Numeric(15, 2), nullable=False, comment='成交额')
    
    # 买盘五档
    bid_price_1 = Column(Numeric(10, 3), comment='买一价')
    bid_volume_1 = Column(Integer, comment='买一量')
    bid_price_2 = Column(Numeric(10, 3), comment='买二价')
    bid_volume_2 = Column(Integer, comment='买二量')
    bid_price_3 = Column(Numeric(10, 3), comment='买三价')
    bid_volume_3 = Column(Integer, comment='买三量')
    bid_price_4 = Column(Numeric(10, 3), comment='买四价')
    bid_volume_4 = Column(Integer, comment='买四量')
    bid_price_5 = Column(Numeric(10, 3), comment='买五价')
    bid_volume_5 = Column(Integer, comment='买五量')
    
    # 卖盘五档
    ask_price_1 = Column(Numeric(10, 3), comment='卖一价')
    ask_volume_1 = Column(Integer, comment='卖一量')
    ask_price_2 = Column(Numeric(10, 3), comment='卖二价')
    ask_volume_2 = Column(Integer, comment='卖二量')
    ask_price_3 = Column(Numeric(10, 3), comment='卖三价')
    ask_volume_3 = Column(Integer, comment='卖三量')
    ask_price_4 = Column(Numeric(10, 3), comment='卖四价')
    ask_volume_4 = Column(Integer, comment='卖四量')
    ask_price_5 = Column(Numeric(10, 3), comment='卖五价')
    ask_volume_5 = Column(Integer, comment='卖五量')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_timestamp', 'stock_code', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
        Index('idx_last_price', 'last_price'),
    )


class Level2Transaction(BaseModel):
    """Level2逐笔成交表"""
    __tablename__ = 'level2_transactions'
    
    stock_code = Column(String(10), nullable=False, comment='股票代码')
    timestamp = Column(DateTime, nullable=False, comment='成交时间')
    price = Column(Numeric(10, 3), nullable=False, comment='成交价格')
    volume = Column(Integer, nullable=False, comment='成交量')
    amount = Column(Numeric(15, 2), nullable=False, comment='成交额')
    buy_order_no = Column(Integer, comment='买方委托序号')
    sell_order_no = Column(Integer, comment='卖方委托序号')
    trade_type = Column(String(2), comment='成交类型')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_timestamp_trans', 'stock_code', 'timestamp'),
        Index('idx_timestamp_trans', 'timestamp'),
        Index('idx_volume_trans', 'volume'),
        Index('idx_amount_trans', 'amount'),
    )


class Level2OrderDetail(BaseModel):
    """Level2逐笔委托表"""
    __tablename__ = 'level2_order_details'
    
    stock_code = Column(String(10), nullable=False, comment='股票代码')
    timestamp = Column(DateTime, nullable=False, comment='委托时间')
    order_no = Column(Integer, nullable=False, comment='委托序号')
    price = Column(Numeric(10, 3), nullable=False, comment='委托价格')
    volume = Column(Integer, nullable=False, comment='委托量')
    side = Column(String(1), nullable=False, comment='买卖方向(B/S)')
    order_type = Column(String(2), comment='委托类型')
    
    # 索引
    __table_args__ = (
        Index('idx_stock_timestamp_order', 'stock_code', 'timestamp'),
        Index('idx_timestamp_order', 'timestamp'),
        Index('idx_order_no', 'order_no'),
        Index('idx_side', 'side'),
        Index('idx_volume_order', 'volume'),
    )
