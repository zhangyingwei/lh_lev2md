#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
Level2行情数据接收器

功能说明：
1. 建立稳定的Level2行情数据连接
2. 处理连接状态管理（连接、断线、重连）
3. 实现登录认证机制
4. 添加连接健康检查
5. 数据标准化和分发

作者：AI Agent Development Team
版本：v1.0.0
"""

import logging
import threading
import time
from typing import Dict, List, Callable, Optional
from datetime import datetime
import lev2mdapi
from .subscription_manager import SubscriptionManager
from .data_parser import DataParser


class MarketDataReceiver(lev2mdapi.CTORATstpLev2MdSpi):
    """Level2行情数据接收器
    
    负责接收Level2实时行情数据，处理连接管理和数据分发
    继承自CTORATstpLev2MdSpi，实现各种行情数据的回调处理方法
    """

    def __init__(self, config: Dict, data_handler: Optional['DataHandler'] = None):
        """
        初始化行情数据接收器
        
        Args:
            config: 配置参数字典
            data_handler: 数据处理器实例
        """
        super().__init__()
        self.config = config
        self.data_handler = data_handler
        self.api = None
        self.connected = False
        self.login_success = False
        self.subscriptions = set()
        
        # 日志配置
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 连接状态监控
        self.connection_monitor = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 10)
        self.reconnect_interval = config.get('reconnect_interval', 5)  # 秒
        
        # 性能统计
        self.stats = {
            'total_messages': 0,
            'market_data_count': 0,
            'transaction_count': 0,
            'order_detail_count': 0,
            'last_message_time': None,
            'connection_time': None,
            'reconnect_count': 0,
            'login_attempts': 0,
            'subscription_count': 0
        }
        
        # 连接状态锁
        self._connection_lock = threading.Lock()

        # 订阅管理器
        self.subscription_manager = None

        # 数据解析器
        self.data_parser = None

        self.logger.info("MarketDataReceiver初始化完成")

    def initialize(self) -> bool:
        """
        初始化API连接
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.logger.info("开始初始化Level2 API连接")
            
            # 创建API实例
            if self.config.get('connection_type') == 'udp':
                self.api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(
                    lev2mdapi.TORA_TSTP_MST_MCAST,
                    self.config.get('cache_mode', False)
                )
                self.api.RegisterMulticast(
                    self.config['multicast_address'],
                    self.config['interface_ip'],
                    ""
                )
                self.logger.info(f"UDP组播模式初始化: {self.config['multicast_address']}")
            else:
                self.api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(
                    lev2mdapi.TORA_TSTP_MST_TCP,
                    self.config.get('cache_mode', False)
                )
                self.api.RegisterFront(self.config['tcp_address'])
                self.logger.info(f"TCP模式初始化: {self.config['tcp_address']}")
            
            # 注册回调
            self.api.RegisterSpi(self)

            # 初始化订阅管理器
            self.subscription_manager = SubscriptionManager(self.api, self.config)

            # 初始化数据解析器
            parser_config = self.config.get('data_parser', {})
            self.data_parser = DataParser(parser_config)

            # 启动连接
            self.running = True
            self.api.Init()
            
            # 启动连接监控线程
            self.connection_monitor = threading.Thread(
                target=self._monitor_connection, 
                daemon=True,
                name="ConnectionMonitor"
            )
            self.connection_monitor.start()
            
            self.logger.info("Level2 API初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"Level2 API初始化失败: {e}", exc_info=True)
            return False

    def OnFrontConnected(self):
        """前置连接成功回调"""
        with self._connection_lock:
            self.connected = True
            self.stats['connection_time'] = datetime.now()
            self.reconnect_attempts = 0  # 重置重连计数
            
        self.logger.info("Level2前置连接成功")
        
        # 发送登录请求
        self._send_login_request()

    def OnFrontDisconnected(self, nReason):
        """前置连接断开回调"""
        with self._connection_lock:
            self.connected = False
            self.login_success = False
            
        self.logger.warning(f"Level2前置连接断开, 原因代码: {nReason}")
        
        # 触发重连机制
        self._handle_disconnection(nReason)

    def _send_login_request(self):
        """发送登录请求"""
        try:
            login_req = lev2mdapi.CTORATstpReqUserLoginField()
            
            if self.config.get('connection_type') != 'udp':
                # TCP模式需要填写认证信息
                login_req.LogInAccount = self.config['login_account']
                login_req.Password = self.config['password']
                login_req.LogInAccountType = lev2mdapi.TORA_TSTP_LACT_UnifiedUserID
                
                self.logger.info(f"发送TCP登录请求: {self.config['login_account']}")
            else:
                self.logger.info("发送UDP登录请求")
            
            self.stats['login_attempts'] += 1
            result = self.api.ReqUserLogin(login_req, self.stats['login_attempts'])
            if result != 0:
                self.logger.error(f"登录请求发送失败: {result}")
                
        except Exception as e:
            self.logger.error(f"发送登录请求异常: {e}", exc_info=True)

    def OnRspUserLogin(self, pRspUserLoginField, pRspInfo, nRequestID, bIsLast):
        """用户登录响应回调"""
        if pRspInfo['ErrorID'] == 0:
            self.login_success = True
            self.logger.info(f"Level2登录成功, RequestID: {nRequestID}")
            
            # 登录成功后开始订阅行情
            self._subscribe_market_data()
            
        else:
            self.login_success = False
            self.logger.error(f"Level2登录失败: [{pRspInfo['ErrorID']}] {pRspInfo['ErrorMsg']}")
            
            # 登录失败时触发重连
            if pRspInfo['ErrorID'] in [439, 440]:  # 账号相关错误
                self.logger.error("账号认证失败，请检查登录信息")
            else:
                self._schedule_reconnect()

    def _subscribe_market_data(self):
        """订阅行情数据"""
        try:
            if not self.subscription_manager:
                self.logger.error("订阅管理器未初始化")
                return

            # 获取订阅配置
            subscriptions = self.config.get('subscriptions', {})

            # 订阅快照行情
            if subscriptions.get('market_data', False):
                securities = subscriptions.get('securities', ['00000000'])
                # 转换字节格式为字符串格式
                if isinstance(securities[0], bytes):
                    securities = [sec.decode('utf-8') for sec in securities]

                exchange = subscriptions.get('exchange', 'COMM')
                if exchange == 'TORA_TSTP_EXD_COMM':
                    exchange = 'COMM'
                elif exchange == 'TORA_TSTP_EXD_SSE':
                    exchange = 'SSE'
                elif exchange == 'TORA_TSTP_EXD_SZSE':
                    exchange = 'SZSE'

                success = self.subscription_manager.subscribe_market_data(securities, exchange)
                if success:
                    self.stats['subscription_count'] += 1
                    self.logger.info(f"快照行情订阅请求发送成功: {len(securities)}个证券")

            # 订阅逐笔成交
            if subscriptions.get('transaction', False):
                securities = subscriptions.get('transaction_securities', ['00000000'])
                if isinstance(securities[0], bytes):
                    securities = [sec.decode('utf-8') for sec in securities]

                success = self.subscription_manager.subscribe_transaction(securities, 'SZSE')
                if success:
                    self.stats['subscription_count'] += 1
                    self.logger.info(f"逐笔成交订阅请求发送成功: {len(securities)}个证券")

            # 订阅逐笔委托
            if subscriptions.get('order_detail', False):
                securities = subscriptions.get('order_securities', ['00000000'])
                if isinstance(securities[0], bytes):
                    securities = [sec.decode('utf-8') for sec in securities]

                success = self.subscription_manager.subscribe_order_detail(securities, 'SZSE')
                if success:
                    self.stats['subscription_count'] += 1
                    self.logger.info(f"逐笔委托订阅请求发送成功: {len(securities)}个证券")

        except Exception as e:
            self.logger.error(f"订阅行情数据异常: {e}", exc_info=True)

    def OnRtnMarketData(self, pMarketData, FirstLevelBuyNum, FirstLevelBuyOrderVolumes,
                       FirstLevelSellNum, FirstLevelSellOrderVolumes):
        """快照行情数据推送回调"""
        try:
            self.stats['total_messages'] += 1
            self.stats['market_data_count'] += 1
            self.stats['last_message_time'] = datetime.now()

            # 使用数据解析器解析数据
            if self.data_parser:
                parsed_data = self.data_parser.parse_market_data(
                    pMarketData,
                    FirstLevelBuyNum,
                    FirstLevelBuyOrderVolumes,
                    FirstLevelSellNum,
                    FirstLevelSellOrderVolumes
                )

                if parsed_data:
                    # 记录详细日志
                    self.logger.debug(
                        f"接收快照行情: {parsed_data['stock_code']} "
                        f"价格:{parsed_data['last_price']:.4f} "
                        f"成交量:{parsed_data['volume']} "
                        f"时间戳:{parsed_data['timestamp']}"
                    )

                    # 分发数据
                    if self.data_handler:
                        self.data_handler.handle_market_data(parsed_data)
                else:
                    self.logger.warning("快照行情数据解析失败")
            else:
                self.logger.error("数据解析器未初始化")

        except Exception as e:
            self.logger.error(f"处理快照行情数据异常: {e}", exc_info=True)

    def OnRtnTransaction(self, pTransaction):
        """逐笔成交数据推送回调"""
        try:
            self.stats['total_messages'] += 1
            self.stats['transaction_count'] += 1
            self.stats['last_message_time'] = datetime.now()

            # 使用数据解析器解析数据
            if self.data_parser:
                parsed_data = self.data_parser.parse_transaction(pTransaction)

                if parsed_data:
                    # 记录详细日志
                    self.logger.debug(
                        f"接收逐笔成交: {parsed_data['stock_code']} "
                        f"价格:{parsed_data['trade_price']:.4f} "
                        f"数量:{parsed_data['trade_volume']} "
                        f"方向:{parsed_data.get('trade_direction', 'unknown')}"
                    )

                    # 分发数据
                    if self.data_handler:
                        self.data_handler.handle_transaction_data(parsed_data)
                else:
                    self.logger.warning("逐笔成交数据解析失败")
            else:
                self.logger.error("数据解析器未初始化")

        except Exception as e:
            self.logger.error(f"处理逐笔成交数据异常: {e}", exc_info=True)

    def OnRtnOrderDetail(self, pOrderDetail):
        """逐笔委托数据推送回调"""
        try:
            self.stats['total_messages'] += 1
            self.stats['order_detail_count'] += 1
            self.stats['last_message_time'] = datetime.now()

            # 使用数据解析器解析数据
            if self.data_parser:
                parsed_data = self.data_parser.parse_order_detail(pOrderDetail)

                if parsed_data:
                    # 记录详细日志
                    self.logger.debug(
                        f"接收逐笔委托: {parsed_data['stock_code']} "
                        f"价格:{parsed_data['price']:.4f} "
                        f"数量:{parsed_data['volume']} "
                        f"方向:{parsed_data.get('order_direction', 'unknown')}"
                    )

                    # 分发数据
                    if self.data_handler:
                        self.data_handler.handle_order_detail_data(parsed_data)
                else:
                    self.logger.warning("逐笔委托数据解析失败")
            else:
                self.logger.error("数据解析器未初始化")

        except Exception as e:
            self.logger.error(f"处理逐笔委托数据异常: {e}", exc_info=True)

    def OnRspSubMarketData(self, pSpecificSecurityField, pRspInfo, nRequestID, bIsLast):
        """快照行情订阅响应回调"""
        try:
            if pRspInfo['ErrorID'] == 0:
                security_id = pSpecificSecurityField['SecurityID'].decode('utf-8')
                exchange_id = pSpecificSecurityField['ExchangeID'].decode('utf-8')

                self.logger.info(f"快照行情订阅成功: {security_id}@{exchange_id}")

                # 通知订阅管理器
                if self.subscription_manager:
                    exchange_map = {'SSE': 'SSE', 'SZE': 'SZSE', 'SZSE': 'SZSE'}
                    exchange = exchange_map.get(exchange_id, 'COMM')
                    self.subscription_manager.handle_subscription_response(
                        'market_data', [security_id], exchange, True
                    )
            else:
                self.logger.error(
                    f"快照行情订阅失败: [{pRspInfo['ErrorID']}] {pRspInfo['ErrorMsg']}"
                )

        except Exception as e:
            self.logger.error(f"处理快照行情订阅响应异常: {e}", exc_info=True)

    def OnRspSubTransaction(self, pSpecificSecurityField, pRspInfo, nRequestID, bIsLast):
        """逐笔成交订阅响应回调"""
        try:
            if pRspInfo['ErrorID'] == 0:
                security_id = pSpecificSecurityField['SecurityID'].decode('utf-8')
                exchange_id = pSpecificSecurityField['ExchangeID'].decode('utf-8')

                self.logger.info(f"逐笔成交订阅成功: {security_id}@{exchange_id}")

                # 通知订阅管理器
                if self.subscription_manager:
                    self.subscription_manager.handle_subscription_response(
                        'transaction', [security_id], 'SZSE', True
                    )
            else:
                self.logger.error(
                    f"逐笔成交订阅失败: [{pRspInfo['ErrorID']}] {pRspInfo['ErrorMsg']}"
                )

        except Exception as e:
            self.logger.error(f"处理逐笔成交订阅响应异常: {e}", exc_info=True)

    def OnRspSubOrderDetail(self, pSpecificSecurityField, pRspInfo, nRequestID, bIsLast):
        """逐笔委托订阅响应回调"""
        try:
            if pRspInfo['ErrorID'] == 0:
                security_id = pSpecificSecurityField['SecurityID'].decode('utf-8')
                exchange_id = pSpecificSecurityField['ExchangeID'].decode('utf-8')

                self.logger.info(f"逐笔委托订阅成功: {security_id}@{exchange_id}")

                # 通知订阅管理器
                if self.subscription_manager:
                    self.subscription_manager.handle_subscription_response(
                        'order_detail', [security_id], 'SZSE', True
                    )
            else:
                self.logger.error(
                    f"逐笔委托订阅失败: [{pRspInfo['ErrorID']}] {pRspInfo['ErrorMsg']}"
                )

        except Exception as e:
            self.logger.error(f"处理逐笔委托订阅响应异常: {e}", exc_info=True)

    def _monitor_connection(self):
        """连接状态监控线程"""
        self.logger.info("启动连接状态监控线程")

        while self.running:
            try:
                # 检查连接状态
                if not self.connected and self.running:
                    self.logger.warning("检测到连接断开，尝试重连...")
                    self._schedule_reconnect()

                # 检查数据接收状态
                if (self.stats['last_message_time'] and
                    (datetime.now() - self.stats['last_message_time']).seconds > 30):
                    self.logger.warning("超过30秒未收到数据，可能存在问题")

                # 记录统计信息
                if self.stats['total_messages'] > 0 and self.stats['total_messages'] % 10000 == 0:
                    self.logger.info(
                        f"数据接收统计: 总消息数:{self.stats['total_messages']} "
                        f"快照:{self.stats['market_data_count']} "
                        f"成交:{self.stats['transaction_count']} "
                        f"委托:{self.stats['order_detail_count']}"
                    )

                time.sleep(10)  # 每10秒检查一次

            except Exception as e:
                self.logger.error(f"连接监控异常: {e}", exc_info=True)
                time.sleep(5)

        self.logger.info("连接状态监控线程已退出")

    def _handle_disconnection(self, reason_code: int):
        """处理连接断开"""
        self.logger.warning(f"处理连接断开事件, 原因代码: {reason_code}")

        # 根据断开原因采取不同策略
        if reason_code in [1, 2, 3]:  # 网络相关错误
            self.logger.info("网络连接问题，将尝试重连")
            self._schedule_reconnect()
        else:
            self.logger.error(f"未知断开原因: {reason_code}")
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        """安排重连"""
        if not self.running:
            return

        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error(f"重连次数已达上限 {self.max_reconnect_attempts}，停止重连")
            return

        self.reconnect_attempts += 1
        self.stats['reconnect_count'] += 1

        self.logger.info(
            f"第 {self.reconnect_attempts}/{self.max_reconnect_attempts} 次重连尝试，"
            f"{self.reconnect_interval}秒后开始"
        )

        # 在新线程中执行重连，避免阻塞
        reconnect_thread = threading.Thread(
            target=self._execute_reconnect,
            daemon=True,
            name=f"Reconnect-{self.reconnect_attempts}"
        )
        reconnect_thread.start()

    def _execute_reconnect(self):
        """执行重连操作"""
        try:
            time.sleep(self.reconnect_interval)

            if not self.running:
                return

            self.logger.info("开始执行重连...")

            # 释放旧的API实例
            if self.api:
                try:
                    self.api.Release()
                except:
                    pass
                self.api = None

            # 重新初始化
            if self.initialize():
                self.logger.info("重连成功")
            else:
                self.logger.error("重连失败")

        except Exception as e:
            self.logger.error(f"执行重连异常: {e}", exc_info=True)

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.login_success

    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['connected'] = self.connected
        stats['login_success'] = self.login_success
        stats['reconnect_attempts'] = self.reconnect_attempts
        stats['running'] = self.running
        return stats

    def shutdown(self):
        """关闭连接"""
        self.logger.info("开始关闭Level2连接")
        self.running = False

        # 等待监控线程结束
        if self.connection_monitor and self.connection_monitor.is_alive():
            self.connection_monitor.join(timeout=5)

        # 释放API资源
        if self.api:
            try:
                self.api.Release()
                self.logger.info("Level2 API已释放")
            except Exception as e:
                self.logger.error(f"释放API异常: {e}")
            finally:
                self.api = None

        self.logger.info("Level2连接已关闭")

    # 订阅管理便捷方法
    def subscribe_securities(self, securities: List[str], data_types: List[str] = None,
                           exchange: str = 'COMM') -> bool:
        """
        订阅指定证券的行情数据

        Args:
            securities: 证券代码列表
            data_types: 数据类型列表 ['market_data', 'transaction', 'order_detail']
            exchange: 交易所代码

        Returns:
            bool: 订阅是否成功
        """
        if not self.subscription_manager:
            self.logger.error("订阅管理器未初始化")
            return False

        if data_types is None:
            data_types = ['market_data']

        success_count = 0
        total_count = len(data_types)

        try:
            for data_type in data_types:
                if data_type == 'market_data':
                    if self.subscription_manager.subscribe_market_data(securities, exchange):
                        success_count += 1
                elif data_type == 'transaction':
                    if self.subscription_manager.subscribe_transaction(securities, 'SZSE'):
                        success_count += 1
                elif data_type == 'order_detail':
                    if self.subscription_manager.subscribe_order_detail(securities, 'SZSE'):
                        success_count += 1
                else:
                    self.logger.warning(f"不支持的数据类型: {data_type}")

            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            self.logger.info(
                f"证券订阅完成: {len(securities)}个证券, "
                f"{len(data_types)}种数据类型, 成功率:{success_rate:.1f}%"
            )

            return success_count == total_count

        except Exception as e:
            self.logger.error(f"订阅证券异常: {e}", exc_info=True)
            return False

    def unsubscribe_securities(self, securities: List[str], data_types: List[str] = None,
                             exchange: str = 'COMM') -> bool:
        """
        取消订阅指定证券的行情数据

        Args:
            securities: 证券代码列表
            data_types: 数据类型列表
            exchange: 交易所代码

        Returns:
            bool: 取消订阅是否成功
        """
        if not self.subscription_manager:
            self.logger.error("订阅管理器未初始化")
            return False

        if data_types is None:
            data_types = ['market_data']

        success_count = 0
        total_count = len(data_types)

        try:
            for data_type in data_types:
                if data_type == 'market_data':
                    if self.subscription_manager.unsubscribe_market_data(securities, exchange):
                        success_count += 1
                elif data_type == 'transaction':
                    if self.subscription_manager.unsubscribe_transaction(securities, 'SZSE'):
                        success_count += 1
                elif data_type == 'order_detail':
                    if self.subscription_manager.unsubscribe_order_detail(securities, 'SZSE'):
                        success_count += 1

            return success_count == total_count

        except Exception as e:
            self.logger.error(f"取消订阅证券异常: {e}", exc_info=True)
            return False

    def get_subscription_stats(self) -> Dict:
        """获取订阅统计信息"""
        if not self.subscription_manager:
            return {}

        return self.subscription_manager.get_stats()

    def get_active_subscriptions(self) -> Dict:
        """获取活跃订阅列表"""
        if not self.subscription_manager:
            return {}

        return self.subscription_manager.get_active_subscriptions()

    def get_parser_stats(self) -> Dict:
        """获取数据解析器统计信息"""
        if not self.data_parser:
            return {}

        return self.data_parser.get_stats()
