"""
实时计算引擎

建立实时计算引擎，支持增量计算、缓存优化和性能监控
提供高性能的实时数据处理和算法计算能力
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import weakref

from ..utils.logger import get_logger
from ..utils.exceptions import CalculationException
from ..models import Level2Snapshot, Level2Transaction, Level2OrderDetail
from .limit_up_break_analyzer import LimitUpBreakAnalyzer, LimitUpBreakEvent
from .stock_filter import StockFilterManager, StockRecommendation


@dataclass
class ComputeTask:
    """计算任务"""
    task_id: str
    task_type: str
    stock_code: str
    data: Any
    priority: int = 0
    created_time: datetime = field(default_factory=datetime.now)
    callback: Optional[Callable] = None


@dataclass
class ComputeResult:
    """计算结果"""
    task_id: str
    stock_code: str
    result_type: str
    result_data: Any
    compute_time: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EngineStats:
    """引擎统计信息"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_compute_time: float = 0.0
    queue_size: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    active_workers: int = 0


class IncrementalCache:
    """增量计算缓存
    
    支持增量更新的高性能缓存系统
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化缓存
        
        Args:
            config: 缓存配置
        """
        self.config = config
        self.logger = get_logger('incremental_cache')
        
        # 缓存配置
        self.max_cache_size = config.get('max_cache_size', 10000)
        self.ttl_seconds = config.get('ttl_seconds', 3600)  # 1小时TTL
        self.cleanup_interval = config.get('cleanup_interval', 300)  # 5分钟清理间隔
        
        # 缓存存储
        self.cache_data: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.access_times: Dict[str, datetime] = {}
        
        # 增量数据
        self.incremental_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 统计信息
        self.hits = 0
        self.misses = 0
        
        # 清理任务
        self.cleanup_task = None
        self.is_running = False
        
        # 线程锁
        self._lock = threading.RLock()
        
        self.logger.info("增量计算缓存初始化完成")
    
    def start(self):
        """启动缓存"""
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("增量计算缓存已启动")
    
    async def stop(self):
        """停止缓存"""
        self.is_running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("增量计算缓存已停止")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据或None
        """
        with self._lock:
            if key in self.cache_data:
                # 检查TTL
                if self._is_expired(key):
                    self._remove_key(key)
                    self.misses += 1
                    return None
                
                # 更新访问时间
                self.access_times[key] = datetime.now()
                self.hits += 1
                return self.cache_data[key].copy()
            
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
        """
        with self._lock:
            # 检查缓存大小限制
            if len(self.cache_data) >= self.max_cache_size and key not in self.cache_data:
                self._evict_lru()
            
            self.cache_data[key] = value
            self.cache_timestamps[key] = datetime.now()
            self.access_times[key] = datetime.now()
    
    def update_incremental(self, key: str, data: Any):
        """更新增量数据
        
        Args:
            key: 缓存键
            data: 增量数据
        """
        with self._lock:
            self.incremental_data[key].append({
                'data': data,
                'timestamp': datetime.now()
            })
    
    def get_incremental_data(self, key: str, since: Optional[datetime] = None) -> List[Any]:
        """获取增量数据
        
        Args:
            key: 缓存键
            since: 起始时间
            
        Returns:
            增量数据列表
        """
        with self._lock:
            if key not in self.incremental_data:
                return []
            
            if since is None:
                return [item['data'] for item in self.incremental_data[key]]
            
            return [
                item['data'] for item in self.incremental_data[key]
                if item['timestamp'] >= since
            ]
    
    def invalidate(self, key: str):
        """使缓存失效
        
        Args:
            key: 缓存键
        """
        with self._lock:
            self._remove_key(key)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache_data.clear()
            self.cache_timestamps.clear()
            self.access_times.clear()
            self.incremental_data.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'cache_size': len(self.cache_data),
                'max_cache_size': self.max_cache_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'incremental_keys': len(self.incremental_data)
            }
    
    def _is_expired(self, key: str) -> bool:
        """检查缓存是否过期
        
        Args:
            key: 缓存键
            
        Returns:
            是否过期
        """
        if key not in self.cache_timestamps:
            return True
        
        age = (datetime.now() - self.cache_timestamps[key]).total_seconds()
        return age > self.ttl_seconds
    
    def _remove_key(self, key: str):
        """移除缓存键
        
        Args:
            key: 缓存键
        """
        self.cache_data.pop(key, None)
        self.cache_timestamps.pop(key, None)
        self.access_times.pop(key, None)
        self.incremental_data.pop(key, None)
    
    def _evict_lru(self):
        """LRU淘汰策略"""
        if not self.access_times:
            return
        
        # 找到最久未访问的键
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(lru_key)
    
    async def _cleanup_loop(self):
        """清理循环"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"缓存清理异常: {e}")
    
    def _cleanup_expired(self):
        """清理过期缓存"""
        with self._lock:
            expired_keys = [
                key for key in self.cache_timestamps.keys()
                if self._is_expired(key)
            ]
            
            for key in expired_keys:
                self._remove_key(key)
            
            if expired_keys:
                self.logger.debug(f"清理过期缓存: {len(expired_keys)}个键")


class RealtimeComputeEngine:
    """实时计算引擎
    
    高性能的实时数据处理和算法计算引擎
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化计算引擎
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = get_logger('realtime_engine')
        
        # 引擎配置
        self.max_workers = config.get('max_workers', 4)
        self.queue_size = config.get('queue_size', 10000)
        self.batch_size = config.get('batch_size', 100)
        self.compute_timeout = config.get('compute_timeout', 30.0)
        
        # 任务队列
        self.task_queue = asyncio.Queue(maxsize=self.queue_size)
        self.result_queue = asyncio.Queue(maxsize=self.queue_size)
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 缓存系统
        cache_config = config.get('cache', {})
        self.cache = IncrementalCache(cache_config)
        
        # 算法组件
        analyzer_config = config.get('analyzer', {})
        self.limit_up_analyzer = LimitUpBreakAnalyzer(analyzer_config)
        
        filter_config = config.get('filter', {})
        self.stock_filter = StockFilterManager(filter_config)
        
        # 工作线程
        self.workers = []
        self.is_running = False
        
        # 统计信息
        self.stats = EngineStats()
        self.compute_times = deque(maxlen=1000)
        
        # 结果回调
        self.result_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # 弱引用管理
        self.weak_refs = weakref.WeakSet()
        
        self.logger.info("实时计算引擎初始化完成")
    
    async def start(self) -> bool:
        """启动计算引擎
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.logger.info("启动实时计算引擎...")
            
            self.is_running = True
            
            # 启动缓存
            self.cache.start()
            
            # 启动工作线程
            for i in range(self.max_workers):
                worker = asyncio.create_task(self._worker(f"worker-{i}"))
                self.workers.append(worker)
            
            # 启动结果处理器
            result_processor = asyncio.create_task(self._result_processor())
            self.workers.append(result_processor)
            
            # 启动统计监控
            stats_monitor = asyncio.create_task(self._stats_monitor())
            self.workers.append(stats_monitor)
            
            self.logger.info(f"实时计算引擎启动成功，工作线程数: {self.max_workers}")
            return True
            
        except Exception as e:
            self.logger.error(f"实时计算引擎启动失败: {e}")
            return False

    async def stop(self) -> bool:
        """停止计算引擎

        Returns:
            bool: 停止是否成功
        """
        try:
            self.logger.info("停止实时计算引擎...")

            self.is_running = False

            # 停止工作线程
            for worker in self.workers:
                worker.cancel()

            # 等待工作线程完成
            if self.workers:
                await asyncio.gather(*self.workers, return_exceptions=True)
                self.workers.clear()

            # 停止缓存
            await self.cache.stop()

            # 关闭线程池
            self.thread_pool.shutdown(wait=True)

            self.logger.info("实时计算引擎已停止")
            return True

        except Exception as e:
            self.logger.error(f"实时计算引擎停止失败: {e}")
            return False

    async def submit_task(self, task: ComputeTask) -> bool:
        """提交计算任务

        Args:
            task: 计算任务

        Returns:
            bool: 提交是否成功
        """
        try:
            await self.task_queue.put(task)
            self.stats.total_tasks += 1
            return True
        except asyncio.QueueFull:
            self.logger.warning("任务队列已满，丢弃任务")
            return False
        except Exception as e:
            self.logger.error(f"提交任务失败: {e}")
            return False

    async def process_market_data(self, snapshot: Level2Snapshot, prev_close: Decimal) -> bool:
        """处理快照行情数据

        Args:
            snapshot: 快照数据
            prev_close: 前收盘价

        Returns:
            bool: 处理是否成功
        """
        try:
            # 设置前收盘价
            self.limit_up_analyzer.set_prev_close_price(snapshot.stock_code, prev_close)

            # 创建计算任务
            task = ComputeTask(
                task_id=f"market_{snapshot.stock_code}_{int(time.time() * 1000)}",
                task_type="analyze_snapshot",
                stock_code=snapshot.stock_code,
                data={'snapshot': snapshot, 'prev_close': prev_close},
                priority=1
            )

            return await self.submit_task(task)

        except Exception as e:
            self.logger.error(f"处理快照数据失败: {e}")
            return False

    async def generate_recommendations(self,
                                     filter_preset: str = None,
                                     sort_preset: str = None,
                                     limit: int = 20) -> List[StockRecommendation]:
        """生成股票推荐

        Args:
            filter_preset: 筛选预设
            sort_preset: 排序预设
            limit: 推荐数量限制

        Returns:
            推荐结果列表
        """
        try:
            # 获取所有炸板事件
            all_events = self.limit_up_analyzer.get_all_break_events(min_score=0.0, limit=1000)

            if not all_events:
                return []

            # 生成推荐
            recommendations = self.stock_filter.get_recommendations(
                all_events, filter_preset, sort_preset, limit=limit
            )

            return recommendations

        except Exception as e:
            self.logger.error(f"生成推荐失败: {e}")
            return []

    def add_result_callback(self, result_type: str, callback: Callable):
        """添加结果回调函数

        Args:
            result_type: 结果类型
            callback: 回调函数
        """
        self.result_callbacks[result_type].append(callback)
        self.weak_refs.add(callback)

    async def _worker(self, worker_name: str):
        """工作线程

        Args:
            worker_name: 工作线程名称
        """
        self.logger.debug(f"工作线程 {worker_name} 启动")

        while self.is_running:
            try:
                # 获取任务
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)

                # 更新统计
                self.stats.active_workers += 1

                # 执行任务
                start_time = time.time()
                result = await self._execute_task(task)
                compute_time = time.time() - start_time

                # 记录计算时间
                self.compute_times.append(compute_time)

                if result:
                    result.compute_time = compute_time
                    await self.result_queue.put(result)
                    self.stats.completed_tasks += 1
                else:
                    self.stats.failed_tasks += 1

                # 更新统计
                self.stats.active_workers -= 1
                self.stats.queue_size = self.task_queue.qsize()

                # 标记任务完成
                self.task_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"工作线程 {worker_name} 异常: {e}")
                self.stats.failed_tasks += 1
                self.stats.active_workers -= 1

        self.logger.debug(f"工作线程 {worker_name} 停止")

    async def _execute_task(self, task: ComputeTask) -> Optional[ComputeResult]:
        """执行计算任务

        Args:
            task: 计算任务

        Returns:
            计算结果或None
        """
        try:
            # 检查缓存
            cache_key = f"{task.task_type}_{task.stock_code}"
            cached_result = self.cache.get(cache_key)

            if cached_result and self._is_cache_valid(cached_result, task):
                self.stats.cache_hits += 1
                return ComputeResult(
                    task_id=task.task_id,
                    stock_code=task.stock_code,
                    result_type=task.task_type,
                    result_data=cached_result,
                    compute_time=0.0
                )

            self.stats.cache_misses += 1

            # 执行计算
            if task.task_type == "analyze_snapshot":
                result_data = await self._analyze_snapshot_task(task)
            elif task.task_type == "generate_recommendations":
                result_data = await self._generate_recommendations_task(task)
            else:
                self.logger.warning(f"未知任务类型: {task.task_type}")
                return None

            if result_data is None:
                return None

            # 更新缓存
            self.cache.set(cache_key, result_data)
            self.cache.update_incremental(cache_key, result_data)

            return ComputeResult(
                task_id=task.task_id,
                stock_code=task.stock_code,
                result_type=task.task_type,
                result_data=result_data,
                compute_time=0.0  # 将在worker中设置
            )

        except Exception as e:
            self.logger.error(f"执行任务失败: {e}")
            return None

    async def _analyze_snapshot_task(self, task: ComputeTask) -> Optional[Any]:
        """分析快照任务

        Args:
            task: 计算任务

        Returns:
            分析结果或None
        """
        try:
            data = task.data
            snapshot = data['snapshot']

            # 在线程池中执行CPU密集型计算
            loop = asyncio.get_event_loop()
            event = await loop.run_in_executor(
                self.thread_pool,
                self.limit_up_analyzer.analyze_snapshot,
                snapshot
            )

            return {
                'event': event,
                'stock_code': task.stock_code,
                'timestamp': snapshot.timestamp,
                'analysis_type': 'limit_up_break'
            }

        except Exception as e:
            self.logger.error(f"分析快照任务失败: {e}")
            return None

    async def _generate_recommendations_task(self, task: ComputeTask) -> Optional[Any]:
        """生成推荐任务

        Args:
            task: 计算任务

        Returns:
            推荐结果或None
        """
        try:
            data = task.data
            filter_preset = data.get('filter_preset')
            sort_preset = data.get('sort_preset')
            limit = data.get('limit', 20)

            # 在线程池中执行
            loop = asyncio.get_event_loop()
            recommendations = await loop.run_in_executor(
                self.thread_pool,
                self._sync_generate_recommendations,
                filter_preset, sort_preset, limit
            )

            return {
                'recommendations': recommendations,
                'filter_preset': filter_preset,
                'sort_preset': sort_preset,
                'limit': limit,
                'timestamp': datetime.now()
            }

        except Exception as e:
            self.logger.error(f"生成推荐任务失败: {e}")
            return None

    def _sync_generate_recommendations(self, filter_preset: str, sort_preset: str, limit: int) -> List[StockRecommendation]:
        """同步生成推荐（用于线程池执行）"""
        all_events = self.limit_up_analyzer.get_all_break_events(min_score=0.0, limit=1000)
        if not all_events:
            return []

        return self.stock_filter.get_recommendations(
            all_events, filter_preset, sort_preset, limit=limit
        )

    def _is_cache_valid(self, cached_result: Any, task: ComputeTask) -> bool:
        """检查缓存是否有效

        Args:
            cached_result: 缓存结果
            task: 当前任务

        Returns:
            bool: 缓存是否有效
        """
        # 简单的时间基础验证
        if isinstance(cached_result, dict) and 'timestamp' in cached_result:
            cache_time = cached_result['timestamp']
            if isinstance(cache_time, datetime):
                age = (datetime.now() - cache_time).total_seconds()
                return age < 60  # 1分钟内的缓存有效

        return False

    async def _result_processor(self):
        """结果处理器"""
        self.logger.debug("结果处理器启动")

        while self.is_running:
            try:
                # 获取结果
                result = await asyncio.wait_for(self.result_queue.get(), timeout=1.0)

                # 触发回调
                callbacks = self.result_callbacks.get(result.result_type, [])
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(result)
                        else:
                            callback(result)
                    except Exception as e:
                        self.logger.error(f"结果回调失败: {e}")

                # 标记结果处理完成
                self.result_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"结果处理器异常: {e}")

        self.logger.debug("结果处理器停止")

    async def _stats_monitor(self):
        """统计监控"""
        self.logger.debug("统计监控启动")

        while self.is_running:
            try:
                await asyncio.sleep(30)  # 每30秒更新一次统计

                # 更新平均计算时间
                if self.compute_times:
                    self.stats.avg_compute_time = sum(self.compute_times) / len(self.compute_times)

                # 记录统计信息
                self.logger.info(f"引擎统计 - "
                               f"总任务: {self.stats.total_tasks}, "
                               f"完成: {self.stats.completed_tasks}, "
                               f"失败: {self.stats.failed_tasks}, "
                               f"队列: {self.stats.queue_size}, "
                               f"平均耗时: {self.stats.avg_compute_time:.4f}s")

                # 记录缓存统计
                cache_stats = self.cache.get_stats()
                self.logger.info(f"缓存统计 - "
                               f"大小: {cache_stats['cache_size']}, "
                               f"命中率: {cache_stats['hit_rate']:.2%}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"统计监控异常: {e}")

        self.logger.debug("统计监控停止")

    def get_engine_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息

        Returns:
            统计信息字典
        """
        cache_stats = self.cache.get_stats()

        return {
            'engine_stats': {
                'total_tasks': self.stats.total_tasks,
                'completed_tasks': self.stats.completed_tasks,
                'failed_tasks': self.stats.failed_tasks,
                'avg_compute_time': self.stats.avg_compute_time,
                'queue_size': self.stats.queue_size,
                'active_workers': self.stats.active_workers,
                'is_running': self.is_running
            },
            'cache_stats': cache_stats,
            'analyzer_stats': self.limit_up_analyzer.get_statistics()
        }


def create_realtime_engine(config: Dict[str, Any]) -> RealtimeComputeEngine:
    """创建实时计算引擎

    Args:
        config: 配置参数

    Returns:
        RealtimeComputeEngine: 引擎实例
    """
    return RealtimeComputeEngine(config)
