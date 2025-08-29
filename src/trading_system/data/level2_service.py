"""
Level2数据服务

集成Level2数据接收器、实时数据处理器和连接管理器的完整服务
提供统一的Level2数据服务接口，包括连接管理、数据处理、异常恢复等功能
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from ..utils.logger import get_logger
from ..utils.exceptions import Level2ConnectionException
from .level2_receiver import create_level2_receiver
from .realtime_processor import create_realtime_processor
from .connection_manager import create_connection_manager, ConnectionState


class Level2DataService:
    """Level2数据服务
    
    集成的Level2数据服务，提供：
    - Level2数据接收和处理
    - 连接管理和自动重连
    - 数据缓存和存储
    - 性能监控和质量评估
    - 异常处理和恢复
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Level2数据服务
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('level2_service')
        
        # 组件实例
        self.receiver = None
        self.processor = None
        self.connection_manager = None
        
        # 运行状态
        self.is_running = False
        self.is_initialized = False
        
        # 服务统计
        self.service_stats = {
            'start_time': None,
            'total_data_processed': 0,
            'connection_events': 0,
            'error_count': 0
        }
        
        self.logger.info("Level2数据服务初始化完成")
    
    async def initialize(self) -> bool:
        """初始化服务组件
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.logger.info("初始化Level2数据服务组件...")
            
            # 创建Level2数据接收器
            receiver_config = self.config.get('level2', {})
            self.receiver = create_level2_receiver(receiver_config)
            self.logger.info("Level2数据接收器创建成功")
            
            # 创建实时数据处理器
            processor_config = self.config.get('performance', {})
            processor_config.update(self.config.get('database', {}))
            self.processor = create_realtime_processor(processor_config)
            self.logger.info("实时数据处理器创建成功")
            
            # 创建连接管理器
            connection_config = self.config.get('level2', {})
            connection_config.update(self.config.get('monitoring', {}))
            self.connection_manager = create_connection_manager(connection_config)
            self.logger.info("连接管理器创建成功")
            
            # 设置连接实例
            self.connection_manager.set_connection_instance(self.receiver)
            
            # 注册事件回调
            self._register_callbacks()
            
            self.is_initialized = True
            self.logger.info("Level2数据服务组件初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"Level2数据服务初始化失败: {e}")
            return False
    
    def _register_callbacks(self):
        """注册事件回调"""
        # 注册数据接收回调（使用同步包装器）
        if hasattr(self.receiver, 'add_data_callback'):
            self.receiver.add_data_callback('market_data', self._sync_on_market_data)
            self.receiver.add_data_callback('transaction', self._sync_on_transaction)
            self.receiver.add_data_callback('order_detail', self._sync_on_order_detail)
        
        # 注册连接管理器事件回调
        self.connection_manager.add_event_callback('on_connected', self._on_connected)
        self.connection_manager.add_event_callback('on_disconnected', self._on_disconnected)
        self.connection_manager.add_event_callback('on_authenticated', self._on_authenticated)
        self.connection_manager.add_event_callback('on_data_received', self._on_data_received)
        self.connection_manager.add_event_callback('on_error', self._on_error)
        self.connection_manager.add_event_callback('on_reconnect_success', self._on_reconnect_success)
        self.connection_manager.add_event_callback('on_reconnect_failed', self._on_reconnect_failed)
    
    async def start(self) -> bool:
        """启动Level2数据服务
        
        Returns:
            bool: 启动是否成功
        """
        try:
            if not self.is_initialized:
                if not await self.initialize():
                    return False
            
            self.logger.info("启动Level2数据服务...")
            
            # 启动实时数据处理器
            if not await self.processor.start():
                self.logger.error("实时数据处理器启动失败")
                return False
            
            # 启动连接监控
            if not await self.connection_manager.start_monitoring():
                self.logger.error("连接监控启动失败")
                return False
            
            # 启动Level2数据接收器
            if not self.receiver.start():
                self.logger.error("Level2数据接收器启动失败")
                return False
            
            self.is_running = True
            self.service_stats['start_time'] = datetime.now()
            
            self.logger.info("Level2数据服务启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Level2数据服务启动失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止Level2数据服务
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("停止Level2数据服务...")
            
            self.is_running = False
            
            # 停止Level2数据接收器
            if self.receiver:
                self.receiver.stop()
                self.logger.info("Level2数据接收器已停止")
            
            # 停止连接监控
            if self.connection_manager:
                await self.connection_manager.stop_monitoring()
                self.logger.info("连接监控已停止")
            
            # 停止实时数据处理器
            if self.processor:
                await self.processor.stop()
                self.logger.info("实时数据处理器已停止")
            
            self.logger.info("Level2数据服务已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"Level2数据服务停止失败: {e}")
            return False
    
    # 同步回调包装器
    def _sync_on_market_data(self, data):
        """同步快照行情数据回调包装器"""
        asyncio.create_task(self._on_market_data(data))

    def _sync_on_transaction(self, data):
        """同步逐笔成交数据回调包装器"""
        asyncio.create_task(self._on_transaction(data))

    def _sync_on_order_detail(self, data):
        """同步逐笔委托数据回调包装器"""
        asyncio.create_task(self._on_order_detail(data))

    # 数据处理回调
    async def _on_market_data(self, data):
        """快照行情数据回调"""
        try:
            await self.processor.process_data('market_data', data)
            self.service_stats['total_data_processed'] += 1
            
            # 通知连接管理器收到数据
            self.connection_manager.on_data_received('market_data', 1)
            
        except Exception as e:
            self.logger.error(f"处理快照行情数据失败: {e}")
            self.service_stats['error_count'] += 1
    
    async def _on_transaction(self, data):
        """逐笔成交数据回调"""
        try:
            await self.processor.process_data('transaction', data)
            self.service_stats['total_data_processed'] += 1
            
            # 通知连接管理器收到数据
            self.connection_manager.on_data_received('transaction', 1)
            
        except Exception as e:
            self.logger.error(f"处理逐笔成交数据失败: {e}")
            self.service_stats['error_count'] += 1
    
    async def _on_order_detail(self, data):
        """逐笔委托数据回调"""
        try:
            await self.processor.process_data('order_detail', data)
            self.service_stats['total_data_processed'] += 1
            
            # 通知连接管理器收到数据
            self.connection_manager.on_data_received('order_detail', 1)
            
        except Exception as e:
            self.logger.error(f"处理逐笔委托数据失败: {e}")
            self.service_stats['error_count'] += 1
    
    # 连接事件回调
    def _on_connected(self):
        """连接建立回调"""
        self.logger.info("Level2连接已建立")
        self.service_stats['connection_events'] += 1
    
    def _on_disconnected(self, reason_code):
        """连接断开回调"""
        self.logger.warning(f"Level2连接断开，原因码: {reason_code}")
        self.service_stats['connection_events'] += 1
    
    def _on_authenticated(self):
        """认证成功回调"""
        self.logger.info("Level2认证成功")
        self.service_stats['connection_events'] += 1
    
    def _on_data_received(self, data_type, data_count):
        """数据接收回调"""
        self.logger.debug(f"收到数据: {data_type}, 数量: {data_count}")
    
    def _on_error(self, error):
        """错误回调"""
        self.logger.error(f"Level2连接错误: {error}")
        self.service_stats['error_count'] += 1
    
    def _on_reconnect_success(self, attempt_count):
        """重连成功回调"""
        self.logger.info(f"Level2重连成功，尝试次数: {attempt_count}")
        self.service_stats['connection_events'] += 1
    
    def _on_reconnect_failed(self, attempt_count):
        """重连失败回调"""
        self.logger.error(f"Level2重连失败，尝试次数: {attempt_count}")
        self.service_stats['error_count'] += 1
    
    # 服务接口方法
    def subscribe_market_data(self, securities: List[str], exchange_id: str = 'COMM') -> bool:
        """订阅快照行情数据
        
        Args:
            securities: 证券代码列表
            exchange_id: 交易所ID
            
        Returns:
            bool: 订阅是否成功
        """
        if self.receiver and hasattr(self.receiver, 'subscribe_market_data'):
            return self.receiver.subscribe_market_data(securities, exchange_id)
        return False
    
    def subscribe_transaction(self, securities: List[str], exchange_id: str = 'SZSE') -> bool:
        """订阅逐笔成交数据
        
        Args:
            securities: 证券代码列表
            exchange_id: 交易所ID
            
        Returns:
            bool: 订阅是否成功
        """
        if self.receiver and hasattr(self.receiver, 'subscribe_transaction'):
            return self.receiver.subscribe_transaction(securities, exchange_id)
        return False
    
    def subscribe_order_detail(self, securities: List[str], exchange_id: str = 'SZSE') -> bool:
        """订阅逐笔委托数据
        
        Args:
            securities: 证券代码列表
            exchange_id: 交易所ID
            
        Returns:
            bool: 订阅是否成功
        """
        if self.receiver and hasattr(self.receiver, 'subscribe_order_detail'):
            return self.receiver.subscribe_order_detail(securities, exchange_id)
        return False
    
    def get_cached_market_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取缓存的快照行情数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            缓存的数据或None
        """
        if self.processor and hasattr(self.processor, 'get_cached_market_data'):
            return self.processor.get_cached_market_data(stock_code)
        return None
    
    def get_latest_price(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取最新价格
        
        Args:
            stock_code: 股票代码
            
        Returns:
            最新价格信息或None
        """
        if self.processor and hasattr(self.processor, 'get_latest_price'):
            return self.processor.get_latest_price(stock_code)
        return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态
        
        Returns:
            Dict: 服务状态信息
        """
        status = {
            'is_running': self.is_running,
            'is_initialized': self.is_initialized,
            'service_stats': self.service_stats.copy()
        }
        
        # 添加组件状态
        if self.receiver:
            status['receiver_status'] = self.receiver.get_status()
        
        if self.processor:
            status['processor_status'] = self.processor.get_statistics()
        
        if self.connection_manager:
            status['connection_status'] = self.connection_manager.get_connection_status()
            status['health_status'] = self.connection_manager.get_health_status()
        
        return status
    
    def force_reconnect(self):
        """强制重连"""
        if self.connection_manager:
            self.connection_manager.force_reconnect()
    
    def force_flush_buffer(self) -> bool:
        """强制刷新数据缓冲区
        
        Returns:
            bool: 刷新是否成功
        """
        if self.processor and hasattr(self.processor, 'force_flush_buffer'):
            return self.processor.force_flush_buffer()
        return False


def create_level2_service(config: Dict[str, Any]) -> Level2DataService:
    """创建Level2数据服务
    
    Args:
        config: 配置参数
        
    Returns:
        Level2DataService: 服务实例
    """
    return Level2DataService(config)
