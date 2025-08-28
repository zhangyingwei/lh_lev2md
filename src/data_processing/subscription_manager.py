#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
行情数据订阅管理器

功能说明：
1. 管理不同类型行情数据的订阅
2. 实现快照行情、逐笔成交、逐笔委托订阅
3. 支持动态订阅和取消订阅
4. 支持批量订阅和订阅状态管理

作者：AI Agent Development Team
版本：v1.0.0
"""

import logging
import threading
import time
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from enum import Enum
import lev2mdapi


class SubscriptionType(Enum):
    """订阅类型枚举"""
    MARKET_DATA = "market_data"      # 快照行情
    TRANSACTION = "transaction"      # 逐笔成交
    ORDER_DETAIL = "order_detail"    # 逐笔委托
    INDEX = "index"                  # 指数行情
    XTS_MARKET_DATA = "xts_market_data"  # XTS新债快照
    XTS_TICK = "xts_tick"           # XTS新债逐笔
    NGTS_TICK = "ngts_tick"         # NGTS合流逐笔


class SubscriptionStatus(Enum):
    """订阅状态枚举"""
    PENDING = "pending"      # 待订阅
    SUBSCRIBED = "subscribed"  # 已订阅
    FAILED = "failed"        # 订阅失败
    UNSUBSCRIBED = "unsubscribed"  # 已取消订阅


class SubscriptionManager:
    """行情数据订阅管理器
    
    负责管理Level2各种类型行情数据的订阅和取消订阅
    支持动态订阅管理和订阅状态跟踪
    """
    
    def __init__(self, api_instance, config: Dict):
        """
        初始化订阅管理器
        
        Args:
            api_instance: Level2 API实例
            config: 配置参数
        """
        self.api = api_instance
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 订阅状态管理
        self.subscriptions = {}  # {(type, security, exchange): status}
        self.subscription_callbacks = {}  # 订阅响应回调
        
        # 支持的交易所
        self.exchanges = {
            'SSE': lev2mdapi.TORA_TSTP_EXD_SSE,      # 上海证券交易所
            'SZSE': lev2mdapi.TORA_TSTP_EXD_SZSE,    # 深圳证券交易所
            'COMM': lev2mdapi.TORA_TSTP_EXD_COMM     # 通用(全市场)
        }
        
        # 订阅统计
        self.stats = {
            'total_subscriptions': 0,
            'successful_subscriptions': 0,
            'failed_subscriptions': 0,
            'active_subscriptions': 0,
            'subscription_requests': 0,
            'unsubscription_requests': 0,
            'last_subscription_time': None
        }
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 批量订阅配置
        self.batch_size = config.get('batch_size', 100)
        self.batch_timeout = config.get('batch_timeout', 1.0)
        
        self.logger.info("SubscriptionManager初始化完成")
    
    def subscribe_market_data(self, securities: List[str], 
                            exchange: str = 'COMM') -> bool:
        """
        订阅快照行情
        
        Args:
            securities: 证券代码列表
            exchange: 交易所代码 ('SSE', 'SZSE', 'COMM')
            
        Returns:
            bool: 订阅是否成功
        """
        return self._subscribe(SubscriptionType.MARKET_DATA, securities, exchange)
    
    def subscribe_transaction(self, securities: List[str], 
                            exchange: str = 'SZSE') -> bool:
        """
        订阅逐笔成交 (仅深圳支持)
        
        Args:
            securities: 证券代码列表
            exchange: 交易所代码 (仅支持'SZSE')
            
        Returns:
            bool: 订阅是否成功
        """
        if exchange != 'SZSE':
            self.logger.warning("逐笔成交仅深圳交易所支持")
            return False
        
        return self._subscribe(SubscriptionType.TRANSACTION, securities, exchange)
    
    def subscribe_order_detail(self, securities: List[str], 
                             exchange: str = 'SZSE') -> bool:
        """
        订阅逐笔委托 (仅深圳支持)
        
        Args:
            securities: 证券代码列表
            exchange: 交易所代码 (仅支持'SZSE')
            
        Returns:
            bool: 订阅是否成功
        """
        if exchange != 'SZSE':
            self.logger.warning("逐笔委托仅深圳交易所支持")
            return False
        
        return self._subscribe(SubscriptionType.ORDER_DETAIL, securities, exchange)
    
    def subscribe_index(self, securities: List[str], 
                       exchange: str = 'COMM') -> bool:
        """
        订阅指数行情
        
        Args:
            securities: 指数代码列表
            exchange: 交易所代码
            
        Returns:
            bool: 订阅是否成功
        """
        return self._subscribe(SubscriptionType.INDEX, securities, exchange)
    
    def subscribe_xts_market_data(self, securities: List[str], 
                                exchange: str = 'SSE') -> bool:
        """
        订阅XTS新债快照行情 (仅上海支持)
        
        Args:
            securities: 证券代码列表
            exchange: 交易所代码 (仅支持'SSE')
            
        Returns:
            bool: 订阅是否成功
        """
        if exchange != 'SSE':
            self.logger.warning("XTS新债快照仅上海交易所支持")
            return False
        
        return self._subscribe(SubscriptionType.XTS_MARKET_DATA, securities, exchange)
    
    def subscribe_xts_tick(self, securities: List[str], 
                          exchange: str = 'SSE') -> bool:
        """
        订阅XTS新债逐笔数据 (仅上海支持)
        
        Args:
            securities: 证券代码列表
            exchange: 交易所代码 (仅支持'SSE')
            
        Returns:
            bool: 订阅是否成功
        """
        if exchange != 'SSE':
            self.logger.warning("XTS新债逐笔仅上海交易所支持")
            return False
        
        return self._subscribe(SubscriptionType.XTS_TICK, securities, exchange)
    
    def subscribe_ngts_tick(self, securities: List[str], 
                           exchange: str = 'SSE') -> bool:
        """
        订阅NGTS合流逐笔数据 (仅上海支持)
        
        Args:
            securities: 证券代码列表
            exchange: 交易所代码 (仅支持'SSE')
            
        Returns:
            bool: 订阅是否成功
        """
        if exchange != 'SSE':
            self.logger.warning("NGTS合流逐笔仅上海交易所支持")
            return False
        
        return self._subscribe(SubscriptionType.NGTS_TICK, securities, exchange)
    
    def _subscribe(self, sub_type: SubscriptionType, 
                  securities: List[str], exchange: str) -> bool:
        """
        执行订阅操作
        
        Args:
            sub_type: 订阅类型
            securities: 证券代码列表
            exchange: 交易所代码
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if not self.api:
                self.logger.error("API实例未初始化")
                return False
            
            if exchange not in self.exchanges:
                self.logger.error(f"不支持的交易所: {exchange}")
                return False
            
            exchange_id = self.exchanges[exchange]
            
            # 转换证券代码为字节格式
            securities_bytes = [sec.encode('utf-8') if isinstance(sec, str) else sec 
                              for sec in securities]
            
            # 批量处理大量订阅
            if len(securities) > self.batch_size:
                return self._batch_subscribe(sub_type, securities_bytes, exchange_id)
            
            # 执行订阅
            result = self._execute_subscription(sub_type, securities_bytes, exchange_id)
            
            # 更新订阅状态
            with self._lock:
                for security in securities:
                    key = (sub_type.value, security, exchange)
                    if result == 0:
                        self.subscriptions[key] = SubscriptionStatus.PENDING
                        self.stats['subscription_requests'] += 1
                    else:
                        self.subscriptions[key] = SubscriptionStatus.FAILED
                        self.stats['failed_subscriptions'] += 1
                
                self.stats['last_subscription_time'] = datetime.now()
            
            if result == 0:
                self.logger.info(
                    f"订阅请求发送成功: {sub_type.value}, "
                    f"{len(securities)}个证券, 交易所:{exchange}"
                )
                return True
            else:
                self.logger.error(
                    f"订阅请求发送失败: {sub_type.value}, "
                    f"错误代码:{result}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"订阅操作异常: {e}", exc_info=True)
            return False

    def _execute_subscription(self, sub_type: SubscriptionType,
                            securities: List[bytes], exchange_id: int) -> int:
        """
        执行具体的订阅API调用

        Args:
            sub_type: 订阅类型
            securities: 证券代码列表(字节格式)
            exchange_id: 交易所ID

        Returns:
            int: API调用结果码
        """
        try:
            if sub_type == SubscriptionType.MARKET_DATA:
                return self.api.SubscribeMarketData(securities, exchange_id)
            elif sub_type == SubscriptionType.TRANSACTION:
                return self.api.SubscribeTransaction(securities, exchange_id)
            elif sub_type == SubscriptionType.ORDER_DETAIL:
                return self.api.SubscribeOrderDetail(securities, exchange_id)
            elif sub_type == SubscriptionType.INDEX:
                return self.api.SubscribeIndex(securities, exchange_id)
            elif sub_type == SubscriptionType.XTS_MARKET_DATA:
                return self.api.SubscribeXTSMarketData(securities, exchange_id)
            elif sub_type == SubscriptionType.XTS_TICK:
                return self.api.SubscribeXTSTick(securities, exchange_id)
            elif sub_type == SubscriptionType.NGTS_TICK:
                return self.api.SubscribeNGTSTick(securities, exchange_id)
            else:
                self.logger.error(f"不支持的订阅类型: {sub_type}")
                return -1

        except Exception as e:
            self.logger.error(f"执行订阅API调用异常: {e}", exc_info=True)
            return -1

    def _batch_subscribe(self, sub_type: SubscriptionType,
                        securities: List[bytes], exchange_id: int) -> bool:
        """
        批量订阅处理

        Args:
            sub_type: 订阅类型
            securities: 证券代码列表
            exchange_id: 交易所ID

        Returns:
            bool: 批量订阅是否成功
        """
        try:
            self.logger.info(
                f"开始批量订阅: {sub_type.value}, "
                f"总数:{len(securities)}, 批次大小:{self.batch_size}"
            )

            success_count = 0
            total_batches = (len(securities) + self.batch_size - 1) // self.batch_size

            for i in range(0, len(securities), self.batch_size):
                batch = securities[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1

                self.logger.debug(
                    f"处理批次 {batch_num}/{total_batches}, "
                    f"证券数量:{len(batch)}"
                )

                result = self._execute_subscription(sub_type, batch, exchange_id)

                if result == 0:
                    success_count += len(batch)
                    self.logger.debug(f"批次 {batch_num} 订阅成功")
                else:
                    self.logger.error(f"批次 {batch_num} 订阅失败, 错误代码:{result}")

                # 批次间延迟，避免过快发送请求
                if i + self.batch_size < len(securities):
                    time.sleep(self.batch_timeout)

            success_rate = (success_count / len(securities)) * 100
            self.logger.info(
                f"批量订阅完成: 成功率 {success_rate:.2f}% "
                f"({success_count}/{len(securities)})"
            )

            return success_rate > 90  # 90%以上成功率认为批量订阅成功

        except Exception as e:
            self.logger.error(f"批量订阅异常: {e}", exc_info=True)
            return False

    def unsubscribe_market_data(self, securities: List[str],
                              exchange: str = 'COMM') -> bool:
        """
        取消订阅快照行情

        Args:
            securities: 证券代码列表
            exchange: 交易所代码

        Returns:
            bool: 取消订阅是否成功
        """
        return self._unsubscribe(SubscriptionType.MARKET_DATA, securities, exchange)

    def unsubscribe_transaction(self, securities: List[str],
                              exchange: str = 'SZSE') -> bool:
        """
        取消订阅逐笔成交

        Args:
            securities: 证券代码列表
            exchange: 交易所代码

        Returns:
            bool: 取消订阅是否成功
        """
        return self._unsubscribe(SubscriptionType.TRANSACTION, securities, exchange)

    def unsubscribe_order_detail(self, securities: List[str],
                               exchange: str = 'SZSE') -> bool:
        """
        取消订阅逐笔委托

        Args:
            securities: 证券代码列表
            exchange: 交易所代码

        Returns:
            bool: 取消订阅是否成功
        """
        return self._unsubscribe(SubscriptionType.ORDER_DETAIL, securities, exchange)

    def _unsubscribe(self, sub_type: SubscriptionType,
                    securities: List[str], exchange: str) -> bool:
        """
        执行取消订阅操作

        Args:
            sub_type: 订阅类型
            securities: 证券代码列表
            exchange: 交易所代码

        Returns:
            bool: 取消订阅是否成功
        """
        try:
            if not self.api:
                self.logger.error("API实例未初始化")
                return False

            if exchange not in self.exchanges:
                self.logger.error(f"不支持的交易所: {exchange}")
                return False

            exchange_id = self.exchanges[exchange]
            securities_bytes = [sec.encode('utf-8') if isinstance(sec, str) else sec
                              for sec in securities]

            # 执行取消订阅
            result = self._execute_unsubscription(sub_type, securities_bytes, exchange_id)

            # 更新订阅状态
            with self._lock:
                for security in securities:
                    key = (sub_type.value, security, exchange)
                    if result == 0:
                        self.subscriptions[key] = SubscriptionStatus.UNSUBSCRIBED
                        self.stats['unsubscription_requests'] += 1
                        if key in self.subscriptions:
                            self.stats['active_subscriptions'] -= 1

            if result == 0:
                self.logger.info(
                    f"取消订阅请求发送成功: {sub_type.value}, "
                    f"{len(securities)}个证券, 交易所:{exchange}"
                )
                return True
            else:
                self.logger.error(
                    f"取消订阅请求发送失败: {sub_type.value}, "
                    f"错误代码:{result}"
                )
                return False

        except Exception as e:
            self.logger.error(f"取消订阅操作异常: {e}", exc_info=True)
            return False

    def _execute_unsubscription(self, sub_type: SubscriptionType,
                              securities: List[bytes], exchange_id: int) -> int:
        """
        执行具体的取消订阅API调用

        Args:
            sub_type: 订阅类型
            securities: 证券代码列表(字节格式)
            exchange_id: 交易所ID

        Returns:
            int: API调用结果码
        """
        try:
            if sub_type == SubscriptionType.MARKET_DATA:
                return self.api.UnSubscribeMarketData(securities, exchange_id)
            elif sub_type == SubscriptionType.TRANSACTION:
                return self.api.UnSubscribeTransaction(securities, exchange_id)
            elif sub_type == SubscriptionType.ORDER_DETAIL:
                return self.api.UnSubscribeOrderDetail(securities, exchange_id)
            elif sub_type == SubscriptionType.INDEX:
                return self.api.UnSubscribeIndex(securities, exchange_id)
            elif sub_type == SubscriptionType.XTS_MARKET_DATA:
                return self.api.UnSubscribeXTSMarketData(securities, exchange_id)
            elif sub_type == SubscriptionType.XTS_TICK:
                return self.api.UnSubscribeXTSTick(securities, exchange_id)
            elif sub_type == SubscriptionType.NGTS_TICK:
                return self.api.UnSubscribeNGTSTick(securities, exchange_id)
            else:
                self.logger.error(f"不支持的取消订阅类型: {sub_type}")
                return -1

        except Exception as e:
            self.logger.error(f"执行取消订阅API调用异常: {e}", exc_info=True)
            return -1

    def subscribe_all_market_data(self, exchange: str = 'COMM') -> bool:
        """
        订阅全市场快照行情

        Args:
            exchange: 交易所代码

        Returns:
            bool: 订阅是否成功
        """
        return self.subscribe_market_data(['00000000'], exchange)

    def get_subscription_status(self, sub_type: str, security: str,
                              exchange: str) -> Optional[SubscriptionStatus]:
        """
        获取订阅状态

        Args:
            sub_type: 订阅类型
            security: 证券代码
            exchange: 交易所代码

        Returns:
            SubscriptionStatus: 订阅状态
        """
        key = (sub_type, security, exchange)
        with self._lock:
            return self.subscriptions.get(key)

    def get_active_subscriptions(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        获取所有活跃订阅

        Returns:
            Dict: 按订阅类型分组的活跃订阅列表
        """
        active_subs = {}

        with self._lock:
            for (sub_type, security, exchange), status in self.subscriptions.items():
                if status == SubscriptionStatus.SUBSCRIBED:
                    if sub_type not in active_subs:
                        active_subs[sub_type] = []
                    active_subs[sub_type].append((security, exchange))

        return active_subs

    def get_subscription_count(self) -> Dict[str, int]:
        """
        获取各类型订阅数量统计

        Returns:
            Dict: 订阅数量统计
        """
        counts = {}

        with self._lock:
            for (sub_type, _, _), status in self.subscriptions.items():
                if sub_type not in counts:
                    counts[sub_type] = {'total': 0, 'active': 0, 'failed': 0}

                counts[sub_type]['total'] += 1
                if status == SubscriptionStatus.SUBSCRIBED:
                    counts[sub_type]['active'] += 1
                elif status == SubscriptionStatus.FAILED:
                    counts[sub_type]['failed'] += 1

        return counts

    def handle_subscription_response(self, sub_type: str, securities: List[str],
                                   exchange: str, success: bool):
        """
        处理订阅响应

        Args:
            sub_type: 订阅类型
            securities: 证券代码列表
            exchange: 交易所代码
            success: 订阅是否成功
        """
        with self._lock:
            for security in securities:
                key = (sub_type, security, exchange)
                if success:
                    self.subscriptions[key] = SubscriptionStatus.SUBSCRIBED
                    self.stats['successful_subscriptions'] += 1
                    self.stats['active_subscriptions'] += 1
                else:
                    self.subscriptions[key] = SubscriptionStatus.FAILED
                    self.stats['failed_subscriptions'] += 1

        status_text = "成功" if success else "失败"
        self.logger.info(
            f"订阅响应处理: {sub_type}, {len(securities)}个证券, "
            f"交易所:{exchange}, 状态:{status_text}"
        )

    def clear_subscriptions(self):
        """清除所有订阅状态"""
        with self._lock:
            self.subscriptions.clear()
            self.stats['active_subscriptions'] = 0

        self.logger.info("已清除所有订阅状态")

    def get_stats(self) -> Dict:
        """
        获取订阅管理器统计信息

        Returns:
            Dict: 统计信息
        """
        with self._lock:
            stats = self.stats.copy()
            stats['subscription_types'] = len(set(key[0] for key in self.subscriptions.keys()))
            stats['total_securities'] = len(set(key[1] for key in self.subscriptions.keys()))
            stats['success_rate'] = 0

            if stats['subscription_requests'] > 0:
                stats['success_rate'] = (stats['successful_subscriptions'] /
                                       stats['subscription_requests']) * 100

        return stats

    def validate_securities(self, securities: List[str]) -> Tuple[List[str], List[str]]:
        """
        验证证券代码格式

        Args:
            securities: 证券代码列表

        Returns:
            Tuple[List[str], List[str]]: (有效代码列表, 无效代码列表)
        """
        valid_securities = []
        invalid_securities = []

        for security in securities:
            if self._is_valid_security_code(security):
                valid_securities.append(security)
            else:
                invalid_securities.append(security)

        if invalid_securities:
            self.logger.warning(f"发现无效证券代码: {invalid_securities}")

        return valid_securities, invalid_securities

    def _is_valid_security_code(self, security: str) -> bool:
        """
        验证单个证券代码是否有效

        Args:
            security: 证券代码

        Returns:
            bool: 是否有效
        """
        if not security or not isinstance(security, str):
            return False

        # 通配符
        if security == '00000000':
            return True

        # 基本格式检查
        if len(security) != 6 or not security.isdigit():
            return False

        return True
