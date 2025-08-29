"""
连接管理器

负责Level2连接的稳定性管理、自动重连机制和异常恢复处理
提供连接状态监控、故障检测、重连策略和连接质量评估功能
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.exceptions import Level2ConnectionException, retry_on_exception


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"      # 未连接
    CONNECTING = "connecting"          # 连接中
    CONNECTED = "connected"            # 已连接
    AUTHENTICATED = "authenticated"    # 已认证
    RECONNECTING = "reconnecting"      # 重连中
    FAILED = "failed"                  # 连接失败
    SUSPENDED = "suspended"            # 连接暂停


@dataclass
class ConnectionMetrics:
    """连接质量指标"""
    connect_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    total_connects: int = 0
    total_disconnects: int = 0
    total_reconnects: int = 0
    failed_attempts: int = 0
    data_received_count: int = 0
    last_data_time: Optional[datetime] = None
    avg_latency: float = 0.0
    packet_loss_rate: float = 0.0
    connection_uptime: timedelta = field(default_factory=lambda: timedelta())


@dataclass
class ReconnectStrategy:
    """重连策略配置"""
    max_attempts: int = 10              # 最大重连次数
    initial_delay: float = 1.0          # 初始延迟（秒）
    max_delay: float = 60.0             # 最大延迟（秒）
    backoff_factor: float = 2.0         # 退避因子
    jitter: bool = True                 # 是否添加随机抖动
    reset_on_success: bool = True       # 成功后是否重置计数器


class ConnectionManager:
    """连接管理器
    
    负责管理Level2连接的生命周期，包括：
    - 连接状态监控和管理
    - 自动重连机制
    - 异常检测和恢复
    - 连接质量评估
    - 故障转移和负载均衡
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化连接管理器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('connection_manager')
        
        # 连接状态
        self.state = ConnectionState.DISCONNECTED
        self.state_lock = threading.Lock()
        
        # 连接指标
        self.metrics = ConnectionMetrics()
        
        # 重连策略
        self.reconnect_strategy = ReconnectStrategy(
            max_attempts=config.get('max_reconnect_attempts', 10),
            initial_delay=config.get('reconnect_initial_delay', 1.0),
            max_delay=config.get('reconnect_max_delay', 60.0),
            backoff_factor=config.get('reconnect_backoff_factor', 2.0),
            jitter=config.get('reconnect_jitter', True)
        )
        
        # 重连状态
        self.current_attempt = 0
        self.next_reconnect_time = None
        self.reconnect_task = None
        
        # 连接实例
        self.connection_instance = None
        
        # 事件回调
        self.event_callbacks = {
            'on_connected': [],
            'on_disconnected': [],
            'on_authenticated': [],
            'on_reconnect_start': [],
            'on_reconnect_success': [],
            'on_reconnect_failed': [],
            'on_data_received': [],
            'on_error': []
        }
        
        # 健康检查
        self.health_check_enabled = config.get('health_check_enabled', True)
        self.health_check_interval = config.get('health_check_interval', 30.0)
        self.health_check_timeout = config.get('health_check_timeout', 10.0)
        self.health_check_task = None
        
        # 连接质量监控
        self.quality_monitor_enabled = config.get('quality_monitor_enabled', True)
        self.quality_monitor_interval = config.get('quality_monitor_interval', 60.0)
        self.quality_monitor_task = None
        
        # 故障检测
        self.failure_detection_enabled = config.get('failure_detection_enabled', True)
        self.max_no_data_time = config.get('max_no_data_time', 300.0)  # 5分钟无数据视为异常
        self.min_data_rate = config.get('min_data_rate', 1.0)  # 最小数据接收速率（条/秒）
        
        self.logger.info("连接管理器初始化完成")
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """添加事件回调函数
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
        else:
            raise ValueError(f"不支持的事件类型: {event_type}")
    
    def set_connection_instance(self, instance):
        """设置连接实例
        
        Args:
            instance: 连接实例（如Level2DataReceiver）
        """
        self.connection_instance = instance
        self.logger.info("连接实例已设置")
    
    async def start_monitoring(self) -> bool:
        """启动连接监控
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.logger.info("启动连接监控...")
            
            # 启动健康检查
            if self.health_check_enabled:
                self.health_check_task = asyncio.create_task(self._health_check_loop())
                self.logger.info("健康检查已启动")
            
            # 启动质量监控
            if self.quality_monitor_enabled:
                self.quality_monitor_task = asyncio.create_task(self._quality_monitor_loop())
                self.logger.info("质量监控已启动")
            
            self.logger.info("连接监控启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"连接监控启动失败: {e}")
            return False
    
    async def stop_monitoring(self) -> bool:
        """停止连接监控
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("停止连接监控...")
            
            # 停止重连任务
            if self.reconnect_task and not self.reconnect_task.done():
                self.reconnect_task.cancel()
                try:
                    await self.reconnect_task
                except asyncio.CancelledError:
                    pass
            
            # 停止健康检查
            if self.health_check_task and not self.health_check_task.done():
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # 停止质量监控
            if self.quality_monitor_task and not self.quality_monitor_task.done():
                self.quality_monitor_task.cancel()
                try:
                    await self.quality_monitor_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("连接监控已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"连接监控停止失败: {e}")
            return False
    
    def on_connection_established(self):
        """连接建立事件处理"""
        with self.state_lock:
            self.state = ConnectionState.CONNECTED
            self.metrics.connect_time = datetime.now()
            self.metrics.total_connects += 1
            
            # 重置重连计数器
            if self.reconnect_strategy.reset_on_success:
                self.current_attempt = 0
        
        self.logger.info("连接已建立")
        self._trigger_callbacks('on_connected')
    
    def on_authentication_success(self):
        """认证成功事件处理"""
        with self.state_lock:
            self.state = ConnectionState.AUTHENTICATED
        
        self.logger.info("认证成功")
        self._trigger_callbacks('on_authenticated')
    
    def on_connection_lost(self, reason_code: Optional[int] = None):
        """连接丢失事件处理
        
        Args:
            reason_code: 断开原因码
        """
        with self.state_lock:
            previous_state = self.state
            self.state = ConnectionState.DISCONNECTED
            self.metrics.total_disconnects += 1
        
        self.logger.warning(f"连接丢失，原因码: {reason_code}")
        self._trigger_callbacks('on_disconnected', reason_code)
        
        # 如果之前是已连接状态，启动重连
        if previous_state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]:
            self._start_reconnect()
    
    def on_data_received(self, data_type: str, data_count: int = 1):
        """数据接收事件处理
        
        Args:
            data_type: 数据类型
            data_count: 数据数量
        """
        self.metrics.data_received_count += data_count
        self.metrics.last_data_time = datetime.now()
        
        self._trigger_callbacks('on_data_received', data_type, data_count)
    
    def on_error(self, error: Exception):
        """错误事件处理
        
        Args:
            error: 错误对象
        """
        self.logger.error(f"连接错误: {error}")
        self._trigger_callbacks('on_error', error)
        
        # 根据错误类型决定是否重连
        if isinstance(error, Level2ConnectionException):
            self._start_reconnect()
    
    def _start_reconnect(self):
        """启动重连机制"""
        if self.current_attempt >= self.reconnect_strategy.max_attempts:
            self.logger.error(f"重连次数已达上限({self.reconnect_strategy.max_attempts})，停止重连")
            with self.state_lock:
                self.state = ConnectionState.FAILED
            return
        
        if self.reconnect_task and not self.reconnect_task.done():
            self.logger.debug("重连任务已在运行中")
            return
        
        # 启动重连任务
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())
    
    async def _reconnect_loop(self):
        """重连循环"""
        self.logger.info("启动重连机制")
        
        while self.current_attempt < self.reconnect_strategy.max_attempts:
            try:
                self.current_attempt += 1
                
                with self.state_lock:
                    self.state = ConnectionState.RECONNECTING
                
                # 计算重连延迟
                delay = self._calculate_reconnect_delay()
                self.next_reconnect_time = datetime.now() + timedelta(seconds=delay)
                
                self.logger.info(f"第{self.current_attempt}次重连，{delay:.1f}秒后开始")
                self._trigger_callbacks('on_reconnect_start', self.current_attempt, delay)
                
                await asyncio.sleep(delay)
                
                # 执行重连
                if await self._attempt_reconnect():
                    self.logger.info("重连成功")
                    self._trigger_callbacks('on_reconnect_success', self.current_attempt)
                    return
                else:
                    self.logger.warning(f"第{self.current_attempt}次重连失败")
                    self.metrics.failed_attempts += 1
                    
            except asyncio.CancelledError:
                self.logger.info("重连任务被取消")
                return
            except Exception as e:
                self.logger.error(f"重连过程异常: {e}")
                self.metrics.failed_attempts += 1
        
        # 重连失败
        self.logger.error("重连失败，已达最大重试次数")
        with self.state_lock:
            self.state = ConnectionState.FAILED
        self._trigger_callbacks('on_reconnect_failed', self.current_attempt)

    def _calculate_reconnect_delay(self) -> float:
        """计算重连延迟时间

        Returns:
            float: 延迟时间（秒）
        """
        # 指数退避算法
        delay = min(
            self.reconnect_strategy.initial_delay * (
                self.reconnect_strategy.backoff_factor ** (self.current_attempt - 1)
            ),
            self.reconnect_strategy.max_delay
        )

        # 添加随机抖动
        if self.reconnect_strategy.jitter:
            import random
            jitter = delay * 0.1 * random.random()  # 10%的随机抖动
            delay += jitter

        return delay

    async def _attempt_reconnect(self) -> bool:
        """尝试重连

        Returns:
            bool: 重连是否成功
        """
        try:
            if not self.connection_instance:
                self.logger.error("连接实例未设置，无法重连")
                return False

            # 停止当前连接
            if hasattr(self.connection_instance, 'stop'):
                self.connection_instance.stop()

            # 等待一段时间
            await asyncio.sleep(1)

            # 重新启动连接
            if hasattr(self.connection_instance, 'start'):
                success = self.connection_instance.start()
                if success:
                    self.metrics.total_reconnects += 1
                    return True

            return False

        except Exception as e:
            self.logger.error(f"重连尝试失败: {e}")
            return False

    async def _health_check_loop(self):
        """健康检查循环"""
        self.logger.debug("健康检查循环启动")

        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                # 执行健康检查
                is_healthy = await self._perform_health_check()

                if not is_healthy:
                    self.logger.warning("健康检查失败，可能需要重连")
                    # 触发重连
                    self.on_connection_lost(-1)  # 使用-1表示健康检查失败

            except asyncio.CancelledError:
                self.logger.debug("健康检查循环被取消")
                break
            except Exception as e:
                self.logger.error(f"健康检查异常: {e}")

        self.logger.debug("健康检查循环停止")

    async def _perform_health_check(self) -> bool:
        """执行健康检查

        Returns:
            bool: 健康状态
        """
        try:
            # 检查连接状态
            if self.state not in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]:
                return False

            # 检查数据接收情况
            if self.failure_detection_enabled:
                current_time = datetime.now()

                # 检查是否长时间无数据
                if self.metrics.last_data_time:
                    no_data_duration = (current_time - self.metrics.last_data_time).total_seconds()
                    if no_data_duration > self.max_no_data_time:
                        self.logger.warning(f"长时间无数据接收: {no_data_duration:.1f}秒")
                        return False

                # 检查数据接收速率
                if self.metrics.connect_time:
                    uptime = (current_time - self.metrics.connect_time).total_seconds()
                    if uptime > 60:  # 连接超过1分钟后才检查速率
                        data_rate = self.metrics.data_received_count / uptime
                        if data_rate < self.min_data_rate:
                            self.logger.warning(f"数据接收速率过低: {data_rate:.2f} 条/秒")
                            return False

            # 检查连接实例状态
            if self.connection_instance and hasattr(self.connection_instance, 'get_status'):
                status = self.connection_instance.get_status()
                if not status.get('is_connected', False) or not status.get('is_logged_in', False):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"健康检查执行失败: {e}")
            return False

    async def _quality_monitor_loop(self):
        """连接质量监控循环"""
        self.logger.debug("质量监控循环启动")

        while True:
            try:
                await asyncio.sleep(self.quality_monitor_interval)

                # 更新连接质量指标
                self._update_quality_metrics()

                # 记录质量报告
                self._log_quality_report()

            except asyncio.CancelledError:
                self.logger.debug("质量监控循环被取消")
                break
            except Exception as e:
                self.logger.error(f"质量监控异常: {e}")

        self.logger.debug("质量监控循环停止")

    def _update_quality_metrics(self):
        """更新连接质量指标"""
        current_time = datetime.now()

        # 更新连接时长
        if self.metrics.connect_time and self.state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]:
            self.metrics.connection_uptime = current_time - self.metrics.connect_time

        # 更新心跳时间
        self.metrics.last_heartbeat = current_time

        # 计算丢包率（简化实现）
        if self.metrics.total_connects > 0:
            self.metrics.packet_loss_rate = self.metrics.failed_attempts / (
                self.metrics.total_connects + self.metrics.failed_attempts
            )

    def _log_quality_report(self):
        """记录质量报告"""
        uptime_hours = self.metrics.connection_uptime.total_seconds() / 3600

        self.logger.info(f"连接质量报告 - "
                        f"状态: {self.state.value}, "
                        f"运行时长: {uptime_hours:.1f}小时, "
                        f"总连接: {self.metrics.total_connects}, "
                        f"总断开: {self.metrics.total_disconnects}, "
                        f"重连次数: {self.metrics.total_reconnects}, "
                        f"数据接收: {self.metrics.data_received_count}, "
                        f"丢包率: {self.metrics.packet_loss_rate:.2%}")

    def _trigger_callbacks(self, event_type: str, *args, **kwargs):
        """触发事件回调

        Args:
            event_type: 事件类型
            *args: 位置参数
            **kwargs: 关键字参数
        """
        callbacks = self.event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"事件回调执行失败 {event_type}: {e}")

    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态信息

        Returns:
            Dict: 连接状态信息
        """
        with self.state_lock:
            return {
                'state': self.state.value,
                'current_attempt': self.current_attempt,
                'max_attempts': self.reconnect_strategy.max_attempts,
                'next_reconnect_time': self.next_reconnect_time.isoformat() if self.next_reconnect_time else None,
                'metrics': {
                    'connect_time': self.metrics.connect_time.isoformat() if self.metrics.connect_time else None,
                    'last_heartbeat': self.metrics.last_heartbeat.isoformat() if self.metrics.last_heartbeat else None,
                    'total_connects': self.metrics.total_connects,
                    'total_disconnects': self.metrics.total_disconnects,
                    'total_reconnects': self.metrics.total_reconnects,
                    'failed_attempts': self.metrics.failed_attempts,
                    'data_received_count': self.metrics.data_received_count,
                    'last_data_time': self.metrics.last_data_time.isoformat() if self.metrics.last_data_time else None,
                    'connection_uptime_seconds': self.metrics.connection_uptime.total_seconds(),
                    'packet_loss_rate': self.metrics.packet_loss_rate
                }
            }

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态

        Returns:
            Dict: 健康状态信息
        """
        current_time = datetime.now()

        # 计算数据接收速率
        data_rate = 0.0
        if self.metrics.connect_time:
            uptime = (current_time - self.metrics.connect_time).total_seconds()
            if uptime > 0:
                data_rate = self.metrics.data_received_count / uptime

        # 计算无数据时长
        no_data_duration = 0.0
        if self.metrics.last_data_time:
            no_data_duration = (current_time - self.metrics.last_data_time).total_seconds()

        return {
            'is_healthy': self.state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED],
            'state': self.state.value,
            'data_rate': data_rate,
            'no_data_duration': no_data_duration,
            'health_check_enabled': self.health_check_enabled,
            'quality_monitor_enabled': self.quality_monitor_enabled,
            'failure_detection_enabled': self.failure_detection_enabled
        }

    def force_reconnect(self):
        """强制重连"""
        self.logger.info("强制重连")
        self.current_attempt = 0  # 重置重连计数器
        self.on_connection_lost(-999)  # 使用特殊代码表示强制重连

    def suspend_reconnect(self):
        """暂停重连"""
        self.logger.info("暂停重连")
        with self.state_lock:
            self.state = ConnectionState.SUSPENDED

        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()

    def resume_reconnect(self):
        """恢复重连"""
        self.logger.info("恢复重连")
        with self.state_lock:
            if self.state == ConnectionState.SUSPENDED:
                self.state = ConnectionState.DISCONNECTED

        self._start_reconnect()


class ConnectionPool:
    """连接池管理器

    管理多个连接实例，提供负载均衡和故障转移功能
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化连接池

        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('connection_pool')

        # 连接管理器列表
        self.managers: List[ConnectionManager] = []
        self.current_manager_index = 0

        # 连接池配置
        self.pool_size = config.get('pool_size', 1)
        self.failover_enabled = config.get('failover_enabled', True)
        self.load_balance_enabled = config.get('load_balance_enabled', False)

        self.logger.info(f"连接池初始化完成，池大小: {self.pool_size}")

    def add_connection_manager(self, manager: ConnectionManager):
        """添加连接管理器

        Args:
            manager: 连接管理器实例
        """
        self.managers.append(manager)
        self.logger.info(f"添加连接管理器，当前数量: {len(self.managers)}")

    def get_active_manager(self) -> Optional[ConnectionManager]:
        """获取活跃的连接管理器

        Returns:
            ConnectionManager: 活跃的管理器或None
        """
        if not self.managers:
            return None

        # 负载均衡模式
        if self.load_balance_enabled:
            manager = self.managers[self.current_manager_index]
            self.current_manager_index = (self.current_manager_index + 1) % len(self.managers)
            return manager

        # 故障转移模式：返回第一个健康的管理器
        for manager in self.managers:
            status = manager.get_health_status()
            if status['is_healthy']:
                return manager

        # 如果没有健康的管理器，返回第一个
        return self.managers[0] if self.managers else None

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态

        Returns:
            Dict: 连接池状态信息
        """
        healthy_count = 0
        total_connections = 0
        total_data_received = 0

        manager_statuses = []

        for i, manager in enumerate(self.managers):
            status = manager.get_connection_status()
            health = manager.get_health_status()

            if health['is_healthy']:
                healthy_count += 1

            total_connections += status['metrics']['total_connects']
            total_data_received += status['metrics']['data_received_count']

            manager_statuses.append({
                'index': i,
                'state': status['state'],
                'is_healthy': health['is_healthy'],
                'data_received': status['metrics']['data_received_count']
            })

        return {
            'pool_size': len(self.managers),
            'healthy_count': healthy_count,
            'total_connections': total_connections,
            'total_data_received': total_data_received,
            'failover_enabled': self.failover_enabled,
            'load_balance_enabled': self.load_balance_enabled,
            'managers': manager_statuses
        }


def create_connection_manager(config: Dict[str, Any]) -> ConnectionManager:
    """创建连接管理器

    Args:
        config: 配置参数

    Returns:
        ConnectionManager: 连接管理器实例
    """
    return ConnectionManager(config)


def create_connection_pool(config: Dict[str, Any]) -> ConnectionPool:
    """创建连接池

    Args:
        config: 配置参数

    Returns:
        ConnectionPool: 连接池实例
    """
    return ConnectionPool(config)
