"""
量化交易系统集成服务

统一的系统集成服务，整合数据接收、算法计算和结果输出功能
提供完整的业务逻辑封装和系统生命周期管理
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..utils.logger import get_logger
from ..config import ConfigManager
from ..models.database_init import initialize_database
from ..data import Level2DataService, create_level2_service
from ..algorithms import (
    RealtimeComputeEngine, 
    create_realtime_engine,
    LimitUpBreakEvent,
    StockRecommendation
)


@dataclass
class SystemStatus:
    """系统状态"""
    is_running: bool = False
    start_time: Optional[datetime] = None
    data_service_status: str = "stopped"
    compute_engine_status: str = "stopped"
    total_data_processed: int = 0
    total_events_detected: int = 0
    total_recommendations: int = 0
    last_update_time: Optional[datetime] = None


class TradingSystemService:
    """量化交易系统集成服务
    
    统一管理和协调所有子系统，提供完整的业务功能
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化交易系统服务
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # 设置日志
        self.logger = get_logger('trading_service')
        
        # 初始化数据库
        self._initialize_database()
        
        # 系统状态
        self.status = SystemStatus()
        
        # 子服务
        self.data_service: Optional[Level2DataService] = None
        self.compute_engine: Optional[RealtimeComputeEngine] = None
        
        # 数据缓存
        self.latest_events: List[LimitUpBreakEvent] = []
        self.latest_recommendations: List[StockRecommendation] = []
        
        # 事件回调
        self.event_callbacks: Dict[str, List[Callable]] = {
            'on_break_event': [],
            'on_recommendations_updated': [],
            'on_system_status_changed': []
        }
        
        # 定时任务
        self.periodic_tasks = []
        
        self.logger.info("量化交易系统服务初始化完成")
    
    def _initialize_database(self):
        """初始化数据库"""
        try:
            db_config = self.config.get('database', {}).get('sqlite', {})
            db_url = f"sqlite:///{db_config.get('path', 'data/trading_system.db')}"
            initialize_database(db_url)
            self.logger.info("数据库初始化成功")
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def start(self) -> bool:
        """启动交易系统
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.logger.info("启动量化交易系统...")
            
            # 创建数据服务
            data_config = {
                'level2': self.config.get('level2', {}),
                'performance': self.config.get('performance', {}),
                'database': self.config.get('database', {}),
                'monitoring': self.config.get('monitoring', {})
            }
            
            self.data_service = create_level2_service(data_config)
            
            # 创建计算引擎
            engine_config = {
                'max_workers': self.config.get('performance', {}).get('max_workers', 4),
                'queue_size': self.config.get('performance', {}).get('queue_size', 10000),
                'batch_size': self.config.get('performance', {}).get('batch_size', 100),
                'cache': self.config.get('cache', {}),
                'analyzer': self.config.get('algorithms', {}),
                'filter': self.config.get('filter', {})
            }
            
            self.compute_engine = create_realtime_engine(engine_config)
            
            # 启动计算引擎
            if not await self.compute_engine.start():
                self.logger.error("计算引擎启动失败")
                return False
            
            # 注册数据处理回调
            self._register_data_callbacks()
            
            # 启动数据服务
            if not await self.data_service.start():
                self.logger.error("数据服务启动失败")
                return False
            
            # 启动定时任务
            await self._start_periodic_tasks()
            
            # 更新系统状态
            self.status.is_running = True
            self.status.start_time = datetime.now()
            self.status.data_service_status = "running"
            self.status.compute_engine_status = "running"
            
            self._trigger_status_change()
            
            self.logger.info("量化交易系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"量化交易系统启动失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止交易系统
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("停止量化交易系统...")
            
            # 停止定时任务
            await self._stop_periodic_tasks()
            
            # 停止数据服务
            if self.data_service:
                await self.data_service.stop()
                self.status.data_service_status = "stopped"
            
            # 停止计算引擎
            if self.compute_engine:
                await self.compute_engine.stop()
                self.status.compute_engine_status = "stopped"
            
            # 更新系统状态
            self.status.is_running = False
            self._trigger_status_change()
            
            self.logger.info("量化交易系统已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"量化交易系统停止失败: {e}")
            return False
    
    def _register_data_callbacks(self):
        """注册数据处理回调"""
        if not self.data_service or not self.compute_engine:
            return
        
        # 注册数据接收回调
        if hasattr(self.data_service, 'receiver') and self.data_service.receiver:
            # 这里需要根据实际的数据服务接口来实现
            pass
        
        # 注册计算结果回调
        self.compute_engine.add_result_callback('analyze_snapshot', self._on_break_event_detected)
    
    async def _on_break_event_detected(self, result):
        """炸板事件检测回调
        
        Args:
            result: 计算结果
        """
        try:
            if result.result_data and result.result_data.get('event'):
                event = result.result_data['event']
                if event:
                    # 更新事件缓存
                    self.latest_events.append(event)
                    
                    # 保持最新100个事件
                    if len(self.latest_events) > 100:
                        self.latest_events = self.latest_events[-100:]
                    
                    # 更新统计
                    self.status.total_events_detected += 1
                    self.status.last_update_time = datetime.now()
                    
                    # 触发事件回调
                    self._trigger_event_callbacks('on_break_event', event)
                    
                    # 异步更新推荐
                    asyncio.create_task(self._update_recommendations())
                    
        except Exception as e:
            self.logger.error(f"处理炸板事件失败: {e}")
    
    async def _update_recommendations(self):
        """更新推荐结果"""
        try:
            if not self.compute_engine:
                return
            
            # 生成推荐
            recommendations = await self.compute_engine.generate_recommendations(
                filter_preset='high_quality',
                sort_preset='comprehensive',
                limit=20
            )
            
            # 更新推荐缓存
            self.latest_recommendations = recommendations
            self.status.total_recommendations = len(recommendations)
            
            # 触发推荐更新回调
            self._trigger_event_callbacks('on_recommendations_updated', recommendations)
            
        except Exception as e:
            self.logger.error(f"更新推荐失败: {e}")
    
    async def _start_periodic_tasks(self):
        """启动定时任务"""
        # 定期更新推荐（每5分钟）
        recommendation_task = asyncio.create_task(self._periodic_recommendation_update())
        self.periodic_tasks.append(recommendation_task)
        
        # 定期清理过期数据（每小时）
        cleanup_task = asyncio.create_task(self._periodic_data_cleanup())
        self.periodic_tasks.append(cleanup_task)
        
        # 定期统计报告（每30分钟）
        stats_task = asyncio.create_task(self._periodic_stats_report())
        self.periodic_tasks.append(stats_task)
    
    async def _stop_periodic_tasks(self):
        """停止定时任务"""
        for task in self.periodic_tasks:
            task.cancel()
        
        if self.periodic_tasks:
            await asyncio.gather(*self.periodic_tasks, return_exceptions=True)
            self.periodic_tasks.clear()
    
    async def _periodic_recommendation_update(self):
        """定期推荐更新任务"""
        while self.status.is_running:
            try:
                await asyncio.sleep(300)  # 5分钟
                await self._update_recommendations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"定期推荐更新失败: {e}")
    
    async def _periodic_data_cleanup(self):
        """定期数据清理任务"""
        while self.status.is_running:
            try:
                await asyncio.sleep(3600)  # 1小时
                
                # 清理过期事件（保留24小时内的）
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.latest_events = [
                    event for event in self.latest_events
                    if event.break_time >= cutoff_time
                ]
                
                self.logger.info(f"数据清理完成，保留事件: {len(self.latest_events)}个")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"定期数据清理失败: {e}")
    
    async def _periodic_stats_report(self):
        """定期统计报告任务"""
        while self.status.is_running:
            try:
                await asyncio.sleep(1800)  # 30分钟
                
                # 获取系统统计
                stats = self.get_system_statistics()
                self.logger.info(f"系统统计报告: {stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"定期统计报告失败: {e}")
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """添加事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    def _trigger_event_callbacks(self, event_type: str, *args, **kwargs):
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
    
    def _trigger_status_change(self):
        """触发状态变更事件"""
        self._trigger_event_callbacks('on_system_status_changed', self.status)
    
    # 业务接口方法
    
    async def subscribe_stocks(self, stock_codes: List[str]) -> bool:
        """订阅股票数据
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            bool: 订阅是否成功
        """
        if not self.data_service:
            return False
        
        try:
            # 订阅快照行情
            success1 = self.data_service.subscribe_market_data(stock_codes)
            
            # 订阅逐笔成交
            success2 = self.data_service.subscribe_transaction(stock_codes)
            
            # 订阅逐笔委托
            success3 = self.data_service.subscribe_order_detail(stock_codes)
            
            return success1 and success2 and success3
            
        except Exception as e:
            self.logger.error(f"订阅股票数据失败: {e}")
            return False
    
    def get_latest_events(self, limit: int = 50) -> List[LimitUpBreakEvent]:
        """获取最新炸板事件
        
        Args:
            limit: 返回数量限制
            
        Returns:
            最新事件列表
        """
        return sorted(self.latest_events, key=lambda x: x.break_time, reverse=True)[:limit]
    
    def get_latest_recommendations(self, limit: int = 20) -> List[StockRecommendation]:
        """获取最新推荐
        
        Args:
            limit: 返回数量限制
            
        Returns:
            最新推荐列表
        """
        return self.latest_recommendations[:limit]
    
    def get_system_status(self) -> SystemStatus:
        """获取系统状态
        
        Returns:
            系统状态
        """
        return self.status
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'system_status': {
                'is_running': self.status.is_running,
                'uptime_seconds': 0,
                'data_service_status': self.status.data_service_status,
                'compute_engine_status': self.status.compute_engine_status
            },
            'data_statistics': {
                'total_data_processed': self.status.total_data_processed,
                'total_events_detected': self.status.total_events_detected,
                'total_recommendations': self.status.total_recommendations,
                'latest_events_count': len(self.latest_events),
                'latest_recommendations_count': len(self.latest_recommendations)
            }
        }
        
        # 计算运行时间
        if self.status.start_time:
            uptime = datetime.now() - self.status.start_time
            stats['system_status']['uptime_seconds'] = int(uptime.total_seconds())
        
        # 添加子系统统计
        if self.data_service:
            data_service_stats = self.data_service.get_service_status()
            stats['data_service'] = data_service_stats
        
        if self.compute_engine:
            engine_stats = self.compute_engine.get_engine_stats()
            stats['compute_engine'] = engine_stats
        
        return stats


def create_trading_service(config_path: str = "config/config.yaml") -> TradingSystemService:
    """创建量化交易系统服务
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        TradingSystemService: 服务实例
    """
    return TradingSystemService(config_path)
