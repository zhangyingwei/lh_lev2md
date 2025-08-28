#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
数据处理器

功能说明：
1. 处理Level2数据的验证、转换、存储和分发
2. 异步数据处理队列
3. 批量数据处理
4. 数据订阅者管理

作者：AI Agent Development Team
版本：v1.0.0
"""

import logging
import asyncio
import threading
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json
import queue


class DataHandler:
    """数据处理器
    
    负责处理Level2数据的验证、转换、存储和分发
    """
    
    def __init__(self, config: Dict):
        """
        初始化数据处理器
        
        Args:
            config: 配置参数字典
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 数据订阅者
        self.subscribers = {}
        
        # 数据处理队列
        self.processing_queue = queue.Queue(maxsize=config.get('queue_size', 10000))
        self.batch_queue = []
        self.batch_size = config.get('batch_size', 100)
        self.batch_timeout = config.get('batch_timeout', 1.0)  # 秒
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=config.get('worker_threads', 4))
        
        # 统计信息
        self.stats = {
            'processed_count': 0,
            'error_count': 0,
            'last_process_time': None,
            'processing_latency': [],
            'batch_count': 0,
            'queue_size': 0
        }
        
        # 处理线程
        self.running = False
        self.process_thread = None
        self.batch_thread = None
        
        self.logger.info("DataHandler初始化完成")
    
    def start_processing(self):
        """启动数据处理"""
        if self.running:
            self.logger.warning("数据处理器已在运行")
            return
        
        self.running = True
        
        # 启动处理线程
        self.process_thread = threading.Thread(
            target=self._process_data_loop,
            daemon=True,
            name="DataProcessor"
        )
        self.process_thread.start()
        
        # 启动批量处理线程
        self.batch_thread = threading.Thread(
            target=self._batch_process_loop,
            daemon=True,
            name="BatchProcessor"
        )
        self.batch_thread.start()
        
        self.logger.info("数据处理器启动完成")
    
    def handle_market_data(self, market_data: Dict):
        """处理快照行情数据"""
        try:
            start_time = datetime.now()
            
            # 添加处理时间戳
            market_data['process_time'] = start_time
            
            # 异步处理
            try:
                self.processing_queue.put({
                    'type': 'market_data',
                    'data': market_data,
                    'timestamp': start_time
                }, timeout=0.1)
                
                # 记录处理延迟
                process_latency = (datetime.now() - start_time).total_seconds() * 1000
                self.stats['processing_latency'].append(process_latency)
                
                # 保持延迟统计数组大小
                if len(self.stats['processing_latency']) > 1000:
                    self.stats['processing_latency'] = self.stats['processing_latency'][-1000:]
                
                self.logger.debug(
                    f"快照行情入队: {market_data['stock_code']} "
                    f"延迟:{process_latency:.2f}ms"
                )
                
            except queue.Full:
                self.logger.error("数据处理队列已满，丢弃数据")
                self.stats['error_count'] += 1
                
        except Exception as e:
            self.logger.error(f"处理快照行情数据异常: {e}", exc_info=True)
            self.stats['error_count'] += 1
    
    def handle_transaction_data(self, transaction_data: Dict):
        """处理逐笔成交数据"""
        try:
            start_time = datetime.now()
            
            # 添加处理时间戳
            transaction_data['process_time'] = start_time
            
            # 异步处理
            try:
                self.processing_queue.put({
                    'type': 'transaction',
                    'data': transaction_data,
                    'timestamp': start_time
                }, timeout=0.1)
                
                self.logger.debug(
                    f"逐笔成交入队: {transaction_data['stock_code']} "
                    f"价格:{transaction_data['trade_price']:.4f}"
                )
                
            except queue.Full:
                self.logger.error("数据处理队列已满，丢弃逐笔成交数据")
                self.stats['error_count'] += 1
                
        except Exception as e:
            self.logger.error(f"处理逐笔成交数据异常: {e}", exc_info=True)
            self.stats['error_count'] += 1
    
    def handle_order_detail_data(self, order_data: Dict):
        """处理逐笔委托数据"""
        try:
            start_time = datetime.now()
            
            # 添加处理时间戳
            order_data['process_time'] = start_time
            
            # 异步处理
            try:
                self.processing_queue.put({
                    'type': 'order_detail',
                    'data': order_data,
                    'timestamp': start_time
                }, timeout=0.1)
                
                self.logger.debug(
                    f"逐笔委托入队: {order_data['stock_code']} "
                    f"价格:{order_data['price']:.4f}"
                )
                
            except queue.Full:
                self.logger.error("数据处理队列已满，丢弃逐笔委托数据")
                self.stats['error_count'] += 1
                
        except Exception as e:
            self.logger.error(f"处理逐笔委托数据异常: {e}", exc_info=True)
            self.stats['error_count'] += 1
    
    def _process_data_loop(self):
        """数据处理主循环"""
        self.logger.info("启动数据处理主循环")
        
        while self.running:
            try:
                # 从队列获取数据
                try:
                    item = self.processing_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 处理数据
                self._process_single_item(item)
                
                # 更新统计
                self.stats['processed_count'] += 1
                self.stats['last_process_time'] = datetime.now()
                self.stats['queue_size'] = self.processing_queue.qsize()
                
                # 标记任务完成
                self.processing_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"数据处理循环异常: {e}", exc_info=True)
        
        self.logger.info("数据处理主循环已退出")
    
    def _process_single_item(self, item: Dict):
        """处理单个数据项"""
        try:
            data_type = item['type']
            data = item['data']
            
            # 添加到批量处理队列
            self.batch_queue.append({
                'type': data_type,
                'data': data
            })
            
            # 通知订阅者
            self._notify_subscribers(data_type, data)
            
        except Exception as e:
            self.logger.error(f"处理单个数据项异常: {e}", exc_info=True)
    
    def _batch_process_loop(self):
        """批量处理循环"""
        self.logger.info("启动批量处理循环")
        
        last_batch_time = datetime.now()
        
        while self.running:
            try:
                current_time = datetime.now()
                time_since_last_batch = (current_time - last_batch_time).total_seconds()
                
                if (len(self.batch_queue) >= self.batch_size or 
                    (len(self.batch_queue) > 0 and time_since_last_batch >= self.batch_timeout)):
                    
                    # 执行批量处理
                    self._execute_batch_process()
                    last_batch_time = current_time
                
                threading.Event().wait(0.1)  # 100ms检查一次
                
            except Exception as e:
                self.logger.error(f"批量处理循环异常: {e}", exc_info=True)
        
        # 处理剩余数据
        if self.batch_queue:
            self._execute_batch_process()
        
        self.logger.info("批量处理循环已退出")
    
    def _execute_batch_process(self):
        """执行批量处理"""
        if not self.batch_queue:
            return
        
        try:
            batch_data = self.batch_queue.copy()
            self.batch_queue.clear()
            
            self.logger.debug(f"执行批量处理: {len(batch_data)}条数据")
            
            # 分类数据
            market_data_batch = []
            transaction_batch = []
            order_detail_batch = []
            
            for item in batch_data:
                if item['type'] == 'market_data':
                    market_data_batch.append(item['data'])
                elif item['type'] == 'transaction':
                    transaction_batch.append(item['data'])
                elif item['type'] == 'order_detail':
                    order_detail_batch.append(item['data'])
            
            # 这里可以添加批量存储到数据库的逻辑
            # 目前只是记录日志
            if market_data_batch:
                self.logger.debug(f"批量处理快照行情: {len(market_data_batch)}条")
            if transaction_batch:
                self.logger.debug(f"批量处理逐笔成交: {len(transaction_batch)}条")
            if order_detail_batch:
                self.logger.debug(f"批量处理逐笔委托: {len(order_detail_batch)}条")
            
            # 更新统计
            self.stats['batch_count'] += 1
            
        except Exception as e:
            self.logger.error(f"执行批量处理异常: {e}", exc_info=True)
    
    def subscribe(self, data_type: str, callback: Callable):
        """订阅数据更新"""
        if data_type not in self.subscribers:
            self.subscribers[data_type] = []
        
        self.subscribers[data_type].append(callback)
        self.logger.info(f"添加数据订阅: {data_type}")
    
    def _notify_subscribers(self, data_type: str, data: Dict):
        """通知订阅者"""
        if data_type in self.subscribers:
            for callback in self.subscribers[data_type]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"通知订阅者异常: {e}", exc_info=True)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.stats.copy()
        
        # 计算平均延迟
        if self.stats['processing_latency']:
            stats['avg_latency'] = sum(self.stats['processing_latency']) / len(self.stats['processing_latency'])
            stats['max_latency'] = max(self.stats['processing_latency'])
            stats['min_latency'] = min(self.stats['processing_latency'])
        
        # 队列状态
        stats['queue_size'] = self.processing_queue.qsize()
        stats['batch_queue_size'] = len(self.batch_queue)
        stats['running'] = self.running
        
        return stats
    
    def shutdown(self):
        """关闭数据处理器"""
        self.logger.info("开始关闭数据处理器")
        
        self.running = False
        
        # 等待处理线程结束
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=5)
        
        if self.batch_thread and self.batch_thread.is_alive():
            self.batch_thread.join(timeout=5)
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        self.logger.info("数据处理器已关闭")
