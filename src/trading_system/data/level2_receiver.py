"""
Level2行情数据接收器

基于lev2mdapi实现Level2行情数据接收功能，支持TCP和UDP组播两种连接方式。
严格遵循开发指南.md中的技术规范和最佳实践。
"""

import sys
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from decimal import Decimal

try:
    import lev2mdapi
    LEVA2MDAPI_AVAILABLE = True
except ImportError:
    LEVA2MDAPI_AVAILABLE = False
    lev2mdapi = None

from ..utils.logger import get_logger
from ..utils.exceptions import Level2ConnectionException, retry_on_exception
from ..models import Level2Snapshot, Level2Transaction, Level2OrderDetail, db_manager


class Level2MdSpi:
    """Level2行情数据回调处理类
    
    继承自CTORATstpLev2MdSpi，实现各种行情数据的回调处理方法
    包括连接状态、登录响应、订阅响应和实时行情数据推送的处理
    """
    
    def __init__(self, receiver):
        """初始化回调处理对象

        Args:
            receiver: Level2数据接收器实例
        """
        if LEVA2MDAPI_AVAILABLE:
            lev2mdapi.CTORATstpLev2MdSpi.__init__(self)
        self.receiver = receiver
        self.logger = get_logger('level2_spi')
        
    def OnFrontConnected(self):
        """前置连接成功回调
        
        当与行情服务器建立连接后会触发此回调
        在此方法中进行用户登录操作
        """
        self.logger.info("Level2前置连接成功")
        self.receiver._on_connected()
        
    def OnFrontDisconnected(self, nReason: int):
        """前置连接断开回调
        
        Args:
            nReason: 断开原因码
        """
        self.logger.warning(f"Level2前置连接断开，原因码: {nReason}")
        self.receiver._on_disconnected(nReason)
        
    def OnRspUserLogin(self, pRspUserLoginField, pRspInfo, nRequestID, bIsLast):
        """用户登录响应回调
        
        Args:
            pRspUserLoginField: 登录响应信息
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID
            bIsLast: 是否为最后一条响应
        """
        if pRspInfo and pRspInfo['ErrorID'] == 0:
            self.logger.info(f"Level2登录成功，请求ID: {nRequestID}")
            self.receiver._on_login_success()
        else:
            error_msg = pRspInfo['ErrorMsg'] if pRspInfo else "未知错误"
            self.logger.error(f"Level2登录失败，错误码: {pRspInfo['ErrorID']}, 错误信息: {error_msg}")
            self.receiver._on_login_failed(pRspInfo['ErrorID'], error_msg)
            
    def OnRspUserLogout(self, pRspUserLogoutField, pRspInfo, nRequestID, bIsLast):
        """用户登出响应回调"""
        if pRspInfo and pRspInfo['ErrorID'] == 0:
            self.logger.info(f"Level2登出成功，请求ID: {nRequestID}")
        else:
            error_msg = pRspInfo['ErrorMsg'] if pRspInfo else "未知错误"
            self.logger.error(f"Level2登出失败，错误码: {pRspInfo['ErrorID']}, 错误信息: {error_msg}")
            
    def OnRtnMarketData(self, pMarketData):
        """快照行情数据推送回调
        
        Args:
            pMarketData: 快照行情数据
        """
        try:
            self.receiver._on_market_data(pMarketData)
        except Exception as e:
            self.logger.error(f"处理快照行情数据失败: {e}")
            
    def OnRtnTransaction(self, pTransaction):
        """逐笔成交数据推送回调
        
        Args:
            pTransaction: 逐笔成交数据
        """
        try:
            self.receiver._on_transaction_data(pTransaction)
        except Exception as e:
            self.logger.error(f"处理逐笔成交数据失败: {e}")
            
    def OnRtnOrderDetail(self, pOrderDetail):
        """逐笔委托数据推送回调
        
        Args:
            pOrderDetail: 逐笔委托数据
        """
        try:
            self.receiver._on_order_detail_data(pOrderDetail)
        except Exception as e:
            self.logger.error(f"处理逐笔委托数据失败: {e}")
            
    def OnRspSubMarketData(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """订阅快照行情响应回调"""
        if pRspInfo and pRspInfo['ErrorID'] == 0:
            security_id = pSpecificSecurity['SecurityID'] if pSpecificSecurity else "全部"
            self.logger.info(f"订阅快照行情成功: {security_id}")
        else:
            error_msg = pRspInfo['ErrorMsg'] if pRspInfo else "未知错误"
            self.logger.error(f"订阅快照行情失败，错误码: {pRspInfo['ErrorID']}, 错误信息: {error_msg}")
            
    def OnRspSubTransaction(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """订阅逐笔成交响应回调"""
        if pRspInfo and pRspInfo['ErrorID'] == 0:
            security_id = pSpecificSecurity['SecurityID'] if pSpecificSecurity else "全部"
            self.logger.info(f"订阅逐笔成交成功: {security_id}")
        else:
            error_msg = pRspInfo['ErrorMsg'] if pRspInfo else "未知错误"
            self.logger.error(f"订阅逐笔成交失败，错误码: {pRspInfo['ErrorID']}, 错误信息: {error_msg}")
            
    def OnRspSubOrderDetail(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """订阅逐笔委托响应回调"""
        if pRspInfo and pRspInfo['ErrorID'] == 0:
            security_id = pSpecificSecurity['SecurityID'] if pSpecificSecurity else "全部"
            self.logger.info(f"订阅逐笔委托成功: {security_id}")
        else:
            error_msg = pRspInfo['ErrorMsg'] if pRspInfo else "未知错误"
            self.logger.error(f"订阅逐笔委托失败，错误码: {pRspInfo['ErrorID']}, 错误信息: {error_msg}")


class Level2DataReceiver:
    """Level2行情数据接收器
    
    负责连接Level2行情服务器，接收和处理各种类型的行情数据
    支持TCP和UDP组播两种连接方式，具备自动重连和异常恢复能力
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Level2数据接收器
        
        Args:
            config: 配置参数字典
        """
        self.config = config
        self.logger = get_logger('level2_receiver')
        
        # 连接状态
        self.is_connected = False
        self.is_logged_in = False
        self.is_running = False
        
        # API实例和回调对象
        self.api = None
        self.spi = None
        
        # 重连参数
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 10)
        self.reconnect_interval = config.get('reconnect_interval', 5)
        self.current_reconnect_count = 0
        
        # 数据处理回调
        self.data_callbacks = {
            'market_data': [],
            'transaction': [],
            'order_detail': []
        }
        
        # 统计信息
        self.stats = {
            'market_data_count': 0,
            'transaction_count': 0,
            'order_detail_count': 0,
            'last_data_time': None,
            'start_time': None
        }
        
        # 线程锁
        self._lock = threading.Lock()
        
    def add_data_callback(self, data_type: str, callback: Callable):
        """添加数据处理回调函数
        
        Args:
            data_type: 数据类型 ('market_data', 'transaction', 'order_detail')
            callback: 回调函数
        """
        if data_type in self.data_callbacks:
            self.data_callbacks[data_type].append(callback)
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")
            
    def start(self) -> bool:
        """启动Level2数据接收器
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.logger.info("正在启动Level2数据接收器...")
            
            # 创建API实例
            connection_mode = self.config.get('connection_mode', 'tcp')
            cache_mode = self.config.get('cache_mode', True)
            
            if connection_mode.lower() == 'tcp':
                self.api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(
                    lev2mdapi.TORA_TSTP_MST_TCP, cache_mode
                )
                # 注册TCP前置地址
                tcp_address = self.config.get('tcp_address', 'tcp://127.0.0.1:6900')
                self.api.RegisterFront(tcp_address)
                self.logger.info(f"使用TCP模式连接: {tcp_address}")
                
            elif connection_mode.lower() == 'multicast':
                self.api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(
                    lev2mdapi.TORA_TSTP_MST_MCAST, cache_mode
                )
                # 注册UDP组播地址
                multicast_address = self.config.get('multicast_address', '224.0.0.1:9999')
                interface_ip = self.config.get('interface_ip', '0.0.0.0')
                self.api.RegisterMulticast(multicast_address, interface_ip, "")
                self.logger.info(f"使用UDP组播模式连接: {multicast_address}")
                
            else:
                raise ValueError(f"不支持的连接模式: {connection_mode}")
            
            # 创建并注册回调对象
            self.spi = Level2MdSpi(self)
            self.api.RegisterSpi(self.spi)
            
            # 初始化API
            self.api.Init()
            
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            self.logger.info("Level2数据接收器启动成功")
            return True

        except Exception as e:
            self.logger.error(f"Level2数据接收器启动失败: {e}")
            return False

    def stop(self) -> bool:
        """停止Level2数据接收器

        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("正在停止Level2数据接收器...")

            self.is_running = False

            if self.api:
                # 登出用户
                if self.is_logged_in:
                    logout_req = lev2mdapi.CTORATstpReqUserLogoutField()
                    self.api.ReqUserLogout(logout_req, 999)
                    time.sleep(1)  # 等待登出完成

                # 释放API资源
                self.api.Release()
                self.api = None

            self.is_connected = False
            self.is_logged_in = False

            self.logger.info("Level2数据接收器已停止")
            return True

        except Exception as e:
            self.logger.error(f"Level2数据接收器停止失败: {e}")
            return False

    @retry_on_exception(max_attempts=3, delay=1.0)
    def _login(self):
        """执行用户登录"""
        if not self.api or not self.is_connected:
            raise Level2ConnectionException("API未初始化或未连接")

        login_req = lev2mdapi.CTORATstpReqUserLoginField()

        # 获取登录配置
        user_id = self.config.get('user_id', '')
        password = self.config.get('password', '')

        if user_id and password:
            # TCP模式需要填写认证信息
            login_req.LogInAccount = user_id
            login_req.Password = password
            login_req.LogInAccountType = lev2mdapi.TORA_TSTP_LACT_UnifiedUserID
            self.logger.info(f"使用认证信息登录: {user_id}")
        else:
            # UDP组播模式可以不填写认证信息
            self.logger.info("使用匿名方式登录")

        # 发送登录请求
        ret = self.api.ReqUserLogin(login_req, 1)
        if ret != 0:
            raise Level2ConnectionException(f"发送登录请求失败，返回码: {ret}")

    def subscribe_market_data(self, securities: List[str], exchange_id: str = 'COMM') -> bool:
        """订阅快照行情数据

        Args:
            securities: 证券代码列表，支持通配符如['00000000']表示全部
            exchange_id: 交易所ID ('SSE', 'SZSE', 'COMM')

        Returns:
            bool: 订阅是否成功
        """
        if not self.is_logged_in:
            self.logger.error("未登录，无法订阅行情数据")
            return False

        try:
            # 转换交易所ID
            exchange_map = {
                'SSE': lev2mdapi.TORA_TSTP_EXD_SSE,
                'SZSE': lev2mdapi.TORA_TSTP_EXD_SZSE,
                'COMM': lev2mdapi.TORA_TSTP_EXD_COMM
            }

            if exchange_id not in exchange_map:
                raise ValueError(f"不支持的交易所ID: {exchange_id}")

            # 转换证券代码为字节数组
            security_bytes = [sec.encode('utf-8') for sec in securities]

            # 发送订阅请求
            ret = self.api.SubscribeMarketData(security_bytes, exchange_map[exchange_id])
            if ret == 0:
                self.logger.info(f"订阅快照行情成功: {securities} @ {exchange_id}")
                return True
            else:
                self.logger.error(f"订阅快照行情失败，返回码: {ret}")
                return False

        except Exception as e:
            self.logger.error(f"订阅快照行情异常: {e}")
            return False

    def subscribe_transaction(self, securities: List[str], exchange_id: str = 'SZSE') -> bool:
        """订阅逐笔成交数据（仅深圳支持）

        Args:
            securities: 证券代码列表
            exchange_id: 交易所ID，默认深圳

        Returns:
            bool: 订阅是否成功
        """
        if not self.is_logged_in:
            self.logger.error("未登录，无法订阅逐笔成交数据")
            return False

        try:
            exchange_map = {
                'SZSE': lev2mdapi.TORA_TSTP_EXD_SZSE
            }

            if exchange_id not in exchange_map:
                raise ValueError(f"逐笔成交仅支持深圳交易所")

            security_bytes = [sec.encode('utf-8') for sec in securities]
            ret = self.api.SubscribeTransaction(security_bytes, exchange_map[exchange_id])

            if ret == 0:
                self.logger.info(f"订阅逐笔成交成功: {securities} @ {exchange_id}")
                return True
            else:
                self.logger.error(f"订阅逐笔成交失败，返回码: {ret}")
                return False

        except Exception as e:
            self.logger.error(f"订阅逐笔成交异常: {e}")
            return False

    def subscribe_order_detail(self, securities: List[str], exchange_id: str = 'SZSE') -> bool:
        """订阅逐笔委托数据（仅深圳支持）

        Args:
            securities: 证券代码列表
            exchange_id: 交易所ID，默认深圳

        Returns:
            bool: 订阅是否成功
        """
        if not self.is_logged_in:
            self.logger.error("未登录，无法订阅逐笔委托数据")
            return False

        try:
            exchange_map = {
                'SZSE': lev2mdapi.TORA_TSTP_EXD_SZSE
            }

            if exchange_id not in exchange_map:
                raise ValueError(f"逐笔委托仅支持深圳交易所")

            security_bytes = [sec.encode('utf-8') for sec in securities]
            ret = self.api.SubscribeOrderDetail(security_bytes, exchange_map[exchange_id])

            if ret == 0:
                self.logger.info(f"订阅逐笔委托成功: {securities} @ {exchange_id}")
                return True
            else:
                self.logger.error(f"订阅逐笔委托失败，返回码: {ret}")
                return False

        except Exception as e:
            self.logger.error(f"订阅逐笔委托异常: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取接收器状态信息

        Returns:
            Dict: 状态信息字典
        """
        with self._lock:
            return {
                'is_running': self.is_running,
                'is_connected': self.is_connected,
                'is_logged_in': self.is_logged_in,
                'reconnect_count': self.current_reconnect_count,
                'stats': self.stats.copy(),
                'config': {
                    'connection_mode': self.config.get('connection_mode'),
                    'tcp_address': self.config.get('tcp_address'),
                    'multicast_address': self.config.get('multicast_address')
                }
            }

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据接收统计信息

        Returns:
            Dict: 统计信息字典
        """
        with self._lock:
            stats = self.stats.copy()
            if stats['start_time']:
                runtime = datetime.now() - stats['start_time']
                stats['runtime_seconds'] = runtime.total_seconds()

                # 计算数据接收速率
                if stats['runtime_seconds'] > 0:
                    stats['market_data_rate'] = stats['market_data_count'] / stats['runtime_seconds']
                    stats['transaction_rate'] = stats['transaction_count'] / stats['runtime_seconds']
                    stats['order_detail_rate'] = stats['order_detail_count'] / stats['runtime_seconds']

            return stats

    # 内部回调方法
    def _on_connected(self):
        """连接成功处理"""
        with self._lock:
            self.is_connected = True
            self.current_reconnect_count = 0

        # 自动登录
        try:
            self._login()
        except Exception as e:
            self.logger.error(f"自动登录失败: {e}")

    def _on_disconnected(self, reason_code: int):
        """连接断开处理"""
        with self._lock:
            self.is_connected = False
            self.is_logged_in = False

        # 启动重连机制
        if self.is_running:
            self._start_reconnect(reason_code)

    def _on_login_success(self):
        """登录成功处理"""
        with self._lock:
            self.is_logged_in = True

        # 执行默认订阅
        self._default_subscriptions()

    def _on_login_failed(self, error_code: int, error_msg: str):
        """登录失败处理"""
        with self._lock:
            self.is_logged_in = False

        # 记录登录失败
        raise Level2ConnectionException(f"登录失败: {error_code} - {error_msg}", error_code)

    def _start_reconnect(self, reason_code: int):
        """启动重连机制"""
        if self.current_reconnect_count >= self.max_reconnect_attempts:
            self.logger.error(f"重连次数已达上限({self.max_reconnect_attempts})，停止重连")
            return

        def reconnect_worker():
            """重连工作线程"""
            self.current_reconnect_count += 1
            self.logger.info(f"开始第{self.current_reconnect_count}次重连，断开原因: {reason_code}")

            time.sleep(self.reconnect_interval)

            try:
                # 重新启动连接
                if self.api:
                    self.api.Release()
                    self.api = None

                # 重新初始化
                if self.start():
                    self.logger.info("重连成功")
                else:
                    self.logger.error("重连失败")

            except Exception as e:
                self.logger.error(f"重连异常: {e}")

        # 在后台线程中执行重连
        reconnect_thread = threading.Thread(target=reconnect_worker, daemon=True)
        reconnect_thread.start()

    def _default_subscriptions(self):
        """执行默认订阅"""
        try:
            # 订阅全市场快照行情
            default_securities = self.config.get('default_securities', ['00000000'])
            default_exchange = self.config.get('default_exchange', 'COMM')

            self.subscribe_market_data(default_securities, default_exchange)

            # 如果配置了深圳逐笔数据订阅
            if self.config.get('enable_szse_tick', False):
                szse_securities = self.config.get('szse_securities', ['00000000'])
                self.subscribe_transaction(szse_securities, 'SZSE')
                self.subscribe_order_detail(szse_securities, 'SZSE')

        except Exception as e:
            self.logger.error(f"默认订阅失败: {e}")

    def _on_market_data(self, market_data):
        """处理快照行情数据"""
        try:
            # 更新统计信息
            with self._lock:
                self.stats['market_data_count'] += 1
                self.stats['last_data_time'] = datetime.now()

            # 转换为数据模型
            snapshot = self._convert_market_data(market_data)

            # 保存到数据库
            self._save_market_data(snapshot)

            # 调用回调函数
            for callback in self.data_callbacks['market_data']:
                try:
                    callback(snapshot)
                except Exception as e:
                    self.logger.error(f"快照行情回调函数执行失败: {e}")

        except Exception as e:
            self.logger.error(f"处理快照行情数据失败: {e}")

    def _on_transaction_data(self, transaction):
        """处理逐笔成交数据"""
        try:
            # 更新统计信息
            with self._lock:
                self.stats['transaction_count'] += 1
                self.stats['last_data_time'] = datetime.now()

            # 转换为数据模型
            trans_data = self._convert_transaction_data(transaction)

            # 保存到数据库
            self._save_transaction_data(trans_data)

            # 调用回调函数
            for callback in self.data_callbacks['transaction']:
                try:
                    callback(trans_data)
                except Exception as e:
                    self.logger.error(f"逐笔成交回调函数执行失败: {e}")

        except Exception as e:
            self.logger.error(f"处理逐笔成交数据失败: {e}")

    def _on_order_detail_data(self, order_detail):
        """处理逐笔委托数据"""
        try:
            # 更新统计信息
            with self._lock:
                self.stats['order_detail_count'] += 1
                self.stats['last_data_time'] = datetime.now()

            # 转换为数据模型
            order_data = self._convert_order_detail_data(order_detail)

            # 保存到数据库
            self._save_order_detail_data(order_data)

            # 调用回调函数
            for callback in self.data_callbacks['order_detail']:
                try:
                    callback(order_data)
                except Exception as e:
                    self.logger.error(f"逐笔委托回调函数执行失败: {e}")

        except Exception as e:
            self.logger.error(f"处理逐笔委托数据失败: {e}")

    def _convert_market_data(self, market_data) -> Level2Snapshot:
        """转换快照行情数据为数据模型

        Args:
            market_data: lev2mdapi快照行情数据

        Returns:
            Level2Snapshot: 快照行情数据模型
        """
        return Level2Snapshot(
            stock_code=market_data.get('SecurityID', ''),
            timestamp=self._parse_timestamp(market_data.get('DataTimeStamp', 0)),
            last_price=Decimal(str(market_data.get('LastPrice', 0))),
            volume=market_data.get('Volume', 0),
            amount=Decimal(str(market_data.get('Turnover', 0))),

            # 买盘五档
            bid_price_1=Decimal(str(market_data.get('BidPrice1', 0))),
            bid_volume_1=market_data.get('BidVolume1', 0),
            bid_price_2=Decimal(str(market_data.get('BidPrice2', 0))),
            bid_volume_2=market_data.get('BidVolume2', 0),
            bid_price_3=Decimal(str(market_data.get('BidPrice3', 0))),
            bid_volume_3=market_data.get('BidVolume3', 0),
            bid_price_4=Decimal(str(market_data.get('BidPrice4', 0))),
            bid_volume_4=market_data.get('BidVolume4', 0),
            bid_price_5=Decimal(str(market_data.get('BidPrice5', 0))),
            bid_volume_5=market_data.get('BidVolume5', 0),

            # 卖盘五档
            ask_price_1=Decimal(str(market_data.get('AskPrice1', 0))),
            ask_volume_1=market_data.get('AskVolume1', 0),
            ask_price_2=Decimal(str(market_data.get('AskPrice2', 0))),
            ask_volume_2=market_data.get('AskVolume2', 0),
            ask_price_3=Decimal(str(market_data.get('AskPrice3', 0))),
            ask_volume_3=market_data.get('AskVolume3', 0),
            ask_price_4=Decimal(str(market_data.get('AskPrice4', 0))),
            ask_volume_4=market_data.get('AskVolume4', 0),
            ask_price_5=Decimal(str(market_data.get('AskPrice5', 0))),
            ask_volume_5=market_data.get('AskVolume5', 0)
        )

    def _convert_transaction_data(self, transaction) -> Level2Transaction:
        """转换逐笔成交数据为数据模型

        Args:
            transaction: lev2mdapi逐笔成交数据

        Returns:
            Level2Transaction: 逐笔成交数据模型
        """
        return Level2Transaction(
            stock_code=transaction.get('SecurityID', ''),
            timestamp=self._parse_timestamp(transaction.get('TradeTime', 0)),
            price=Decimal(str(transaction.get('TradePrice', 0))),
            volume=transaction.get('TradeVolume', 0),
            amount=Decimal(str(transaction.get('TradePrice', 0))) * transaction.get('TradeVolume', 0),
            buy_order_no=transaction.get('BuyNo', 0),
            sell_order_no=transaction.get('SellNo', 0),
            trade_type=transaction.get('TradeType', '')
        )

    def _convert_order_detail_data(self, order_detail) -> Level2OrderDetail:
        """转换逐笔委托数据为数据模型

        Args:
            order_detail: lev2mdapi逐笔委托数据

        Returns:
            Level2OrderDetail: 逐笔委托数据模型
        """
        return Level2OrderDetail(
            stock_code=order_detail.get('SecurityID', ''),
            timestamp=self._parse_timestamp(order_detail.get('OrderTime', 0)),
            order_no=order_detail.get('OrderNO', 0),
            price=Decimal(str(order_detail.get('Price', 0))),
            volume=order_detail.get('Volume', 0),
            side=order_detail.get('Side', ''),
            order_type=order_detail.get('OrderType', '')
        )

    def _parse_timestamp(self, timestamp: int) -> datetime:
        """解析时间戳

        Args:
            timestamp: 时间戳（可能是多种格式）

        Returns:
            datetime: 解析后的时间对象
        """
        try:
            if timestamp == 0:
                return datetime.now()

            # 根据时间戳长度判断格式
            if timestamp > 1000000000000:  # 毫秒时间戳
                return datetime.fromtimestamp(timestamp / 1000)
            elif timestamp > 1000000000:  # 秒时间戳
                return datetime.fromtimestamp(timestamp)
            else:
                # 可能是时间格式如 HHMMSSsss
                time_str = str(timestamp).zfill(9)
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
                microsecond = int(time_str[6:]) * 1000

                now = datetime.now()
                return now.replace(
                    hour=hour, minute=minute, second=second,
                    microsecond=microsecond
                )
        except Exception as e:
            self.logger.warning(f"时间戳解析失败: {timestamp}, 使用当前时间")
            return datetime.now()

    def _save_market_data(self, snapshot: Level2Snapshot):
        """保存快照行情数据到数据库"""
        try:
            session = db_manager.get_session()
            session.add(snapshot)
            session.commit()
            session.close()
        except Exception as e:
            self.logger.error(f"保存快照行情数据失败: {e}")

    def _save_transaction_data(self, transaction: Level2Transaction):
        """保存逐笔成交数据到数据库"""
        try:
            session = db_manager.get_session()
            session.add(transaction)
            session.commit()
            session.close()
        except Exception as e:
            self.logger.error(f"保存逐笔成交数据失败: {e}")

    def _save_order_detail_data(self, order_detail: Level2OrderDetail):
        """保存逐笔委托数据到数据库"""
        try:
            session = db_manager.get_session()
            session.add(order_detail)
            session.commit()
            session.close()
        except Exception as e:
            self.logger.error(f"保存逐笔委托数据失败: {e}")


def create_level2_receiver(config: Dict[str, Any]):
    """创建Level2数据接收器实例

    Args:
        config: 配置参数字典

    Returns:
        Level2数据接收器实例（真实或模拟）
    """
    if not LEVA2MDAPI_AVAILABLE:
        # 如果lev2mdapi不可用，返回模拟接收器
        from .mock_level2_receiver import MockLevel2DataReceiver
        return MockLevel2DataReceiver(config)
    else:
        return Level2DataReceiver(config)
