"""
实时数据处理器

高性能的实时Level2数据处理机制，支持快照、逐笔成交、逐笔委托数据的
实时处理、缓存、批量存储和性能优化
"""

import asyncio
import threading
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from decimal import Decimal
import redis

from ..utils.logger import get_logger
from ..utils.exceptions import exception_handler, retry_on_exception
from ..models import Level2Snapshot, Level2Transaction, Level2OrderDetail, db_manager


@dataclass
class ProcessingStats:
    """数据处理统计信息"""
    total_processed: int = 0
    market_data_processed: int = 0
    transaction_processed: int = 0
    order_detail_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    db_writes: int = 0
    processing_errors: int = 0
    avg_processing_time: float = 0.0
    last_processing_time: Optional[datetime] = None


class DataBuffer:
    """数据缓冲区
    
    用于批量处理和存储数据，提高数据库写入性能
    """
    
    def __init__(self, max_size: int = 1000, flush_interval: float = 5.0):
        """初始化数据缓冲区
        
        Args:
            max_size: 缓冲区最大大小
            flush_interval: 刷新间隔（秒）
        """
        self.max_size = max_size
        self.flush_interval = flush_interval
        
        # 数据缓冲区
        self.market_data_buffer: deque = deque()
        self.transaction_buffer: deque = deque()
        self.order_detail_buffer: deque = deque()
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 自动刷新
        self.last_flush_time = time.time()
        self.auto_flush_enabled = True
        
        self.logger = get_logger('data_buffer')
    
    def add_market_data(self, data: Level2Snapshot):
        """添加快照行情数据"""
        with self._lock:
            self.market_data_buffer.append(data)
            self._check_flush()
    
    def add_transaction(self, data: Level2Transaction):
        """添加逐笔成交数据"""
        with self._lock:
            self.transaction_buffer.append(data)
            self._check_flush()
    
    def add_order_detail(self, data: Level2OrderDetail):
        """添加逐笔委托数据"""
        with self._lock:
            self.order_detail_buffer.append(data)
            self._check_flush()
    
    def _check_flush(self):
        """检查是否需要刷新"""
        total_size = (len(self.market_data_buffer) + 
                     len(self.transaction_buffer) + 
                     len(self.order_detail_buffer))
        
        current_time = time.time()
        time_elapsed = current_time - self.last_flush_time
        
        # 达到大小限制或时间间隔时刷新
        if total_size >= self.max_size or time_elapsed >= self.flush_interval:
            return self._flush_buffers()
        
        return False
    
    def _flush_buffers(self) -> bool:
        """刷新缓冲区到数据库"""
        try:
            session = db_manager.get_session()
            
            # 批量添加快照数据
            if self.market_data_buffer:
                market_data_list = list(self.market_data_buffer)
                session.add_all(market_data_list)
                self.market_data_buffer.clear()
                self.logger.debug(f"批量保存快照数据: {len(market_data_list)}条")
            
            # 批量添加成交数据
            if self.transaction_buffer:
                transaction_list = list(self.transaction_buffer)
                session.add_all(transaction_list)
                self.transaction_buffer.clear()
                self.logger.debug(f"批量保存成交数据: {len(transaction_list)}条")
            
            # 批量添加委托数据
            if self.order_detail_buffer:
                order_detail_list = list(self.order_detail_buffer)
                session.add_all(order_detail_list)
                self.order_detail_buffer.clear()
                self.logger.debug(f"批量保存委托数据: {len(order_detail_list)}条")
            
            # 提交事务
            session.commit()
            session.close()
            
            self.last_flush_time = time.time()
            return True
            
        except Exception as e:
            self.logger.error(f"批量保存数据失败: {e}")
            session.rollback()
            session.close()
            return False
    
    def force_flush(self) -> bool:
        """强制刷新缓冲区"""
        with self._lock:
            return self._flush_buffers()
    
    def get_buffer_status(self) -> Dict[str, int]:
        """获取缓冲区状态"""
        with self._lock:
            return {
                'market_data_count': len(self.market_data_buffer),
                'transaction_count': len(self.transaction_buffer),
                'order_detail_count': len(self.order_detail_buffer),
                'total_count': (len(self.market_data_buffer) + 
                              len(self.transaction_buffer) + 
                              len(self.order_detail_buffer))
            }


class RedisCache:
    """Redis缓存管理器
    
    用于缓存最新的行情数据，提供快速访问
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Redis缓存
        
        Args:
            config: Redis配置
        """
        self.config = config
        self.logger = get_logger('redis_cache')
        
        try:
            self.redis_client = redis.Redis(
                host=config.get('host', 'localhost'),
                port=config.get('port', 6379),
                db=config.get('db', 0),
                password=config.get('password'),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # 测试连接
            self.redis_client.ping()
            self.logger.info("Redis缓存连接成功")
            self.available = True
            
        except Exception as e:
            self.logger.warning(f"Redis缓存连接失败: {e}，将使用内存缓存")
            self.redis_client = None
            self.available = False
            
            # 使用内存缓存作为备选
            self.memory_cache = {}
    
    def set_market_data(self, stock_code: str, data: Level2Snapshot, expire: int = 300):
        """缓存快照行情数据
        
        Args:
            stock_code: 股票代码
            data: 快照数据
            expire: 过期时间（秒）
        """
        try:
            cache_key = f"market_data:{stock_code}"
            cache_value = {
                'stock_code': data.stock_code,
                'timestamp': data.timestamp.isoformat(),
                'last_price': str(data.last_price),
                'volume': data.volume,
                'amount': str(data.amount),
                'bid_price_1': str(data.bid_price_1),
                'bid_volume_1': data.bid_volume_1,
                'ask_price_1': str(data.ask_price_1),
                'ask_volume_1': data.ask_volume_1
            }
            
            if self.available:
                import json
                self.redis_client.setex(cache_key, expire, json.dumps(cache_value))
            else:
                # 使用内存缓存
                self.memory_cache[cache_key] = {
                    'data': cache_value,
                    'expire_time': time.time() + expire
                }
                
        except Exception as e:
            self.logger.error(f"缓存快照数据失败: {e}")
    
    def get_market_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取缓存的快照行情数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            缓存的数据或None
        """
        try:
            cache_key = f"market_data:{stock_code}"
            
            if self.available:
                import json
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            else:
                # 使用内存缓存
                cached_item = self.memory_cache.get(cache_key)
                if cached_item and time.time() < cached_item['expire_time']:
                    return cached_item['data']
                elif cached_item:
                    # 过期数据，删除
                    del self.memory_cache[cache_key]
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取缓存数据失败: {e}")
            return None
    
    def set_latest_price(self, stock_code: str, price: Decimal, timestamp: datetime):
        """缓存最新价格
        
        Args:
            stock_code: 股票代码
            price: 最新价格
            timestamp: 时间戳
        """
        try:
            cache_key = f"latest_price:{stock_code}"
            cache_value = {
                'price': str(price),
                'timestamp': timestamp.isoformat()
            }
            
            if self.available:
                import json
                self.redis_client.setex(cache_key, 300, json.dumps(cache_value))
            else:
                self.memory_cache[cache_key] = {
                    'data': cache_value,
                    'expire_time': time.time() + 300
                }
                
        except Exception as e:
            self.logger.error(f"缓存最新价格失败: {e}")
    
    def get_latest_price(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取最新价格
        
        Args:
            stock_code: 股票代码
            
        Returns:
            最新价格信息或None
        """
        try:
            cache_key = f"latest_price:{stock_code}"
            
            if self.available:
                import json
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            else:
                cached_item = self.memory_cache.get(cache_key)
                if cached_item and time.time() < cached_item['expire_time']:
                    return cached_item['data']
                elif cached_item:
                    del self.memory_cache[cache_key]
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取最新价格失败: {e}")
            return None
    
    def cleanup_expired(self):
        """清理过期的内存缓存"""
        if not self.available:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.memory_cache.items()
                if current_time >= item['expire_time']
            ]
            for key in expired_keys:
                del self.memory_cache[key]


class RealtimeDataProcessor:
    """实时数据处理器

    高性能的Level2数据实时处理引擎，支持：
    - 数据验证和清洗
    - 批量缓冲和存储
    - Redis缓存管理
    - 性能监控和统计
    - 异步处理和并发控制
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化实时数据处理器

        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('realtime_processor')

        # 性能配置
        self.batch_size = config.get('batch_size', 100)
        self.flush_interval = config.get('flush_interval', 5.0)
        self.max_workers = config.get('max_workers', 4)
        self.queue_size = config.get('queue_size', 10000)

        # 数据缓冲区
        self.data_buffer = DataBuffer(
            max_size=self.batch_size,
            flush_interval=self.flush_interval
        )

        # Redis缓存
        redis_config = config.get('redis', {})
        self.redis_cache = RedisCache(redis_config)

        # 统计信息
        self.stats = ProcessingStats()

        # 数据处理队列
        self.processing_queue = asyncio.Queue(maxsize=self.queue_size)

        # 数据验证器
        self.validators = {
            'market_data': self._validate_market_data,
            'transaction': self._validate_transaction,
            'order_detail': self._validate_order_detail
        }

        # 数据处理器
        self.processors = {
            'market_data': self._process_market_data,
            'transaction': self._process_transaction,
            'order_detail': self._process_order_detail
        }

        # 运行状态
        self.is_running = False
        self.worker_tasks = []

        # 性能监控
        self.processing_times = deque(maxlen=1000)  # 保留最近1000次处理时间

        self.logger.info("实时数据处理器初始化完成")

    async def start(self) -> bool:
        """启动数据处理器

        Returns:
            bool: 启动是否成功
        """
        try:
            self.logger.info("启动实时数据处理器...")

            self.is_running = True

            # 启动工作线程
            for i in range(self.max_workers):
                task = asyncio.create_task(self._worker(f"worker-{i}"))
                self.worker_tasks.append(task)

            # 启动性能监控任务
            monitor_task = asyncio.create_task(self._performance_monitor())
            self.worker_tasks.append(monitor_task)

            self.logger.info(f"实时数据处理器启动成功，工作线程数: {self.max_workers}")
            return True

        except Exception as e:
            self.logger.error(f"实时数据处理器启动失败: {e}")
            return False

    async def stop(self) -> bool:
        """停止数据处理器

        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("停止实时数据处理器...")

            self.is_running = False

            # 等待所有任务完成
            if self.worker_tasks:
                await asyncio.gather(*self.worker_tasks, return_exceptions=True)
                self.worker_tasks.clear()

            # 强制刷新缓冲区
            self.data_buffer.force_flush()

            self.logger.info("实时数据处理器已停止")
            return True

        except Exception as e:
            self.logger.error(f"实时数据处理器停止失败: {e}")
            return False

    async def process_data(self, data_type: str, data: Union[Level2Snapshot, Level2Transaction, Level2OrderDetail]):
        """处理数据

        Args:
            data_type: 数据类型 ('market_data', 'transaction', 'order_detail')
            data: 数据对象
        """
        try:
            # 添加到处理队列
            await self.processing_queue.put((data_type, data))

        except asyncio.QueueFull:
            self.logger.warning("处理队列已满，丢弃数据")
            self.stats.processing_errors += 1
        except Exception as e:
            self.logger.error(f"添加数据到处理队列失败: {e}")
            self.stats.processing_errors += 1

    async def _worker(self, worker_name: str):
        """工作线程

        Args:
            worker_name: 工作线程名称
        """
        self.logger.debug(f"工作线程 {worker_name} 启动")

        while self.is_running:
            try:
                # 从队列获取数据
                data_type, data = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=1.0
                )

                # 记录处理开始时间
                start_time = time.time()

                # 数据验证
                if not self._validate_data(data_type, data):
                    self.stats.processing_errors += 1
                    continue

                # 数据处理
                await self._process_data_item(data_type, data)

                # 记录处理时间
                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)

                # 更新统计
                self.stats.total_processed += 1
                self.stats.last_processing_time = datetime.now()

                # 标记任务完成
                self.processing_queue.task_done()

            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                self.logger.error(f"工作线程 {worker_name} 处理数据异常: {e}")
                self.stats.processing_errors += 1

        self.logger.debug(f"工作线程 {worker_name} 停止")

    def _validate_data(self, data_type: str, data) -> bool:
        """验证数据

        Args:
            data_type: 数据类型
            data: 数据对象

        Returns:
            bool: 验证是否通过
        """
        try:
            validator = self.validators.get(data_type)
            if validator:
                return validator(data)
            return True

        except Exception as e:
            self.logger.error(f"数据验证异常: {e}")
            return False

    async def _process_data_item(self, data_type: str, data):
        """处理单个数据项

        Args:
            data_type: 数据类型
            data: 数据对象
        """
        try:
            processor = self.processors.get(data_type)
            if processor:
                await processor(data)

        except Exception as e:
            self.logger.error(f"处理数据项失败: {e}")
            raise

    def _validate_market_data(self, data: Level2Snapshot) -> bool:
        """验证快照行情数据"""
        if not data.stock_code or len(data.stock_code) < 6:
            return False
        if data.last_price <= 0:
            return False
        if data.volume < 0:
            return False
        return True

    def _validate_transaction(self, data: Level2Transaction) -> bool:
        """验证逐笔成交数据"""
        if not data.stock_code or len(data.stock_code) < 6:
            return False
        if data.price <= 0:
            return False
        if data.volume <= 0:
            return False
        return True

    def _validate_order_detail(self, data: Level2OrderDetail) -> bool:
        """验证逐笔委托数据"""
        if not data.stock_code or len(data.stock_code) < 6:
            return False
        if data.price <= 0:
            return False
        if data.volume <= 0:
            return False
        if data.side not in ['B', 'S']:
            return False
        return True

    async def _process_market_data(self, data: Level2Snapshot):
        """处理快照行情数据"""
        # 缓存到Redis
        self.redis_cache.set_market_data(data.stock_code, data)
        self.redis_cache.set_latest_price(data.stock_code, data.last_price, data.timestamp)

        # 添加到缓冲区
        self.data_buffer.add_market_data(data)

        # 更新统计
        self.stats.market_data_processed += 1

    async def _process_transaction(self, data: Level2Transaction):
        """处理逐笔成交数据"""
        # 添加到缓冲区
        self.data_buffer.add_transaction(data)

        # 更新统计
        self.stats.transaction_processed += 1

    async def _process_order_detail(self, data: Level2OrderDetail):
        """处理逐笔委托数据"""
        # 添加到缓冲区
        self.data_buffer.add_order_detail(data)

        # 更新统计
        self.stats.order_detail_processed += 1

    async def _performance_monitor(self):
        """性能监控任务"""
        self.logger.debug("性能监控任务启动")

        while self.is_running:
            try:
                await asyncio.sleep(30)  # 每30秒监控一次

                # 计算平均处理时间
                if self.processing_times:
                    avg_time = sum(self.processing_times) / len(self.processing_times)
                    self.stats.avg_processing_time = avg_time

                # 获取缓冲区状态
                buffer_status = self.data_buffer.get_buffer_status()

                # 记录性能指标
                self.logger.info(f"性能监控 - "
                               f"总处理: {self.stats.total_processed}, "
                               f"平均耗时: {self.stats.avg_processing_time:.4f}s, "
                               f"缓冲区: {buffer_status['total_count']}, "
                               f"错误: {self.stats.processing_errors}")

                # 清理过期缓存
                self.redis_cache.cleanup_expired()

            except Exception as e:
                self.logger.error(f"性能监控异常: {e}")

        self.logger.debug("性能监控任务停止")

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息

        Returns:
            Dict: 统计信息
        """
        buffer_status = self.data_buffer.get_buffer_status()

        return {
            'total_processed': self.stats.total_processed,
            'market_data_processed': self.stats.market_data_processed,
            'transaction_processed': self.stats.transaction_processed,
            'order_detail_processed': self.stats.order_detail_processed,
            'processing_errors': self.stats.processing_errors,
            'avg_processing_time': self.stats.avg_processing_time,
            'last_processing_time': self.stats.last_processing_time.isoformat() if self.stats.last_processing_time else None,
            'queue_size': self.processing_queue.qsize(),
            'buffer_status': buffer_status,
            'cache_available': self.redis_cache.available,
            'is_running': self.is_running
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标

        Returns:
            Dict: 性能指标
        """
        if not self.processing_times:
            return {
                'avg_processing_time': 0.0,
                'min_processing_time': 0.0,
                'max_processing_time': 0.0,
                'p95_processing_time': 0.0,
                'p99_processing_time': 0.0
            }

        times = sorted(self.processing_times)
        count = len(times)

        return {
            'avg_processing_time': sum(times) / count,
            'min_processing_time': times[0],
            'max_processing_time': times[-1],
            'p95_processing_time': times[int(count * 0.95)] if count > 0 else 0.0,
            'p99_processing_time': times[int(count * 0.99)] if count > 0 else 0.0,
            'sample_count': count
        }

    def force_flush_buffer(self) -> bool:
        """强制刷新数据缓冲区

        Returns:
            bool: 刷新是否成功
        """
        return self.data_buffer.force_flush()

    def get_cached_market_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取缓存的快照行情数据

        Args:
            stock_code: 股票代码

        Returns:
            缓存的数据或None
        """
        cached_data = self.redis_cache.get_market_data(stock_code)
        if cached_data:
            self.stats.cache_hits += 1
        else:
            self.stats.cache_misses += 1
        return cached_data

    def get_latest_price(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取最新价格

        Args:
            stock_code: 股票代码

        Returns:
            最新价格信息或None
        """
        return self.redis_cache.get_latest_price(stock_code)


class DataProcessorManager:
    """数据处理器管理器

    管理多个数据处理器实例，提供负载均衡和故障恢复
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化管理器

        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('processor_manager')

        # 处理器实例
        self.processors = []
        self.processor_count = config.get('processor_count', 1)

        # 负载均衡
        self.current_processor_index = 0

        # 运行状态
        self.is_running = False

    async def start(self) -> bool:
        """启动所有处理器

        Returns:
            bool: 启动是否成功
        """
        try:
            self.logger.info(f"启动数据处理器管理器，处理器数量: {self.processor_count}")

            # 创建并启动处理器
            for i in range(self.processor_count):
                processor_config = self.config.copy()
                processor_config['instance_id'] = i

                processor = RealtimeDataProcessor(processor_config)
                if await processor.start():
                    self.processors.append(processor)
                    self.logger.info(f"处理器 {i} 启动成功")
                else:
                    self.logger.error(f"处理器 {i} 启动失败")
                    return False

            self.is_running = True
            self.logger.info("数据处理器管理器启动成功")
            return True

        except Exception as e:
            self.logger.error(f"数据处理器管理器启动失败: {e}")
            return False

    async def stop(self) -> bool:
        """停止所有处理器

        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("停止数据处理器管理器...")

            self.is_running = False

            # 停止所有处理器
            for i, processor in enumerate(self.processors):
                try:
                    await processor.stop()
                    self.logger.info(f"处理器 {i} 已停止")
                except Exception as e:
                    self.logger.error(f"停止处理器 {i} 失败: {e}")

            self.processors.clear()
            self.logger.info("数据处理器管理器已停止")
            return True

        except Exception as e:
            self.logger.error(f"数据处理器管理器停止失败: {e}")
            return False

    async def process_data(self, data_type: str, data):
        """处理数据（负载均衡）

        Args:
            data_type: 数据类型
            data: 数据对象
        """
        if not self.processors:
            raise RuntimeError("没有可用的数据处理器")

        # 轮询负载均衡
        processor = self.processors[self.current_processor_index]
        self.current_processor_index = (self.current_processor_index + 1) % len(self.processors)

        await processor.process_data(data_type, data)

    def get_aggregated_statistics(self) -> Dict[str, Any]:
        """获取聚合统计信息

        Returns:
            Dict: 聚合统计信息
        """
        if not self.processors:
            return {}

        # 聚合所有处理器的统计信息
        total_stats = {
            'total_processed': 0,
            'market_data_processed': 0,
            'transaction_processed': 0,
            'order_detail_processed': 0,
            'processing_errors': 0,
            'processor_count': len(self.processors),
            'is_running': self.is_running
        }

        for processor in self.processors:
            stats = processor.get_statistics()
            total_stats['total_processed'] += stats.get('total_processed', 0)
            total_stats['market_data_processed'] += stats.get('market_data_processed', 0)
            total_stats['transaction_processed'] += stats.get('transaction_processed', 0)
            total_stats['order_detail_processed'] += stats.get('order_detail_processed', 0)
            total_stats['processing_errors'] += stats.get('processing_errors', 0)

        return total_stats


def create_realtime_processor(config: Dict[str, Any]) -> RealtimeDataProcessor:
    """创建实时数据处理器

    Args:
        config: 配置参数

    Returns:
        RealtimeDataProcessor: 处理器实例
    """
    return RealtimeDataProcessor(config)


def create_processor_manager(config: Dict[str, Any]) -> DataProcessorManager:
    """创建数据处理器管理器

    Args:
        config: 配置参数

    Returns:
        DataProcessorManager: 管理器实例
    """
    return DataProcessorManager(config)
