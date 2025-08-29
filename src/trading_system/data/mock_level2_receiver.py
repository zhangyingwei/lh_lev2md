"""
模拟Level2数据接收器

用于开发和测试环境，模拟Level2行情数据接收功能
当lev2mdapi库不可用时，可以使用此模拟器进行开发和测试
"""

import random
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Callable

from ..utils.logger import get_logger
from ..models import Level2Snapshot, Level2Transaction, Level2OrderDetail, db_manager


class MockLevel2DataReceiver:
    """模拟Level2数据接收器
    
    模拟真实的Level2数据接收器功能，用于开发和测试
    生成模拟的快照行情、逐笔成交和逐笔委托数据
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化模拟接收器
        
        Args:
            config: 配置参数字典
        """
        self.config = config
        self.logger = get_logger('mock_level2_receiver')
        
        # 状态管理
        self.is_running = False
        self.is_connected = False
        self.is_logged_in = False
        
        # 模拟数据生成
        self.data_thread = None
        self.stop_event = threading.Event()
        
        # 数据回调
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
        
        # 模拟股票列表
        self.mock_stocks = [
            '000001', '000002', '600000', '600036', '600519',
            '000858', '002415', '300059', '688981', '688599'
        ]
        
        # 模拟价格数据
        self.stock_prices = {
            stock: {
                'price': Decimal(str(random.uniform(10, 100))),
                'volume': random.randint(1000000, 10000000)
            }
            for stock in self.mock_stocks
        }
        
        self.logger.info("模拟Level2数据接收器初始化完成")
    
    def add_data_callback(self, data_type: str, callback: Callable):
        """添加数据处理回调函数"""
        if data_type in self.data_callbacks:
            self.data_callbacks[data_type].append(callback)
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")
    
    def start(self) -> bool:
        """启动模拟接收器"""
        try:
            self.logger.info("启动模拟Level2数据接收器...")
            
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            # 模拟连接过程
            time.sleep(1)
            self.is_connected = True
            self.logger.info("模拟连接成功")
            
            # 模拟登录过程
            time.sleep(1)
            self.is_logged_in = True
            self.logger.info("模拟登录成功")
            
            # 启动数据生成线程
            self.stop_event.clear()
            self.data_thread = threading.Thread(target=self._data_generator, daemon=True)
            self.data_thread.start()
            
            self.logger.info("模拟Level2数据接收器启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"模拟接收器启动失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止模拟接收器"""
        try:
            self.logger.info("停止模拟Level2数据接收器...")
            
            self.is_running = False
            self.stop_event.set()
            
            if self.data_thread and self.data_thread.is_alive():
                self.data_thread.join(timeout=5)
            
            self.is_connected = False
            self.is_logged_in = False
            
            self.logger.info("模拟Level2数据接收器已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"模拟接收器停止失败: {e}")
            return False
    
    def subscribe_market_data(self, securities: List[str], exchange_id: str = 'COMM') -> bool:
        """模拟订阅快照行情"""
        self.logger.info(f"模拟订阅快照行情: {securities} @ {exchange_id}")
        return True
    
    def subscribe_transaction(self, securities: List[str], exchange_id: str = 'SZSE') -> bool:
        """模拟订阅逐笔成交"""
        self.logger.info(f"模拟订阅逐笔成交: {securities} @ {exchange_id}")
        return True
    
    def subscribe_order_detail(self, securities: List[str], exchange_id: str = 'SZSE') -> bool:
        """模拟订阅逐笔委托"""
        self.logger.info(f"模拟订阅逐笔委托: {securities} @ {exchange_id}")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            'is_running': self.is_running,
            'is_connected': self.is_connected,
            'is_logged_in': self.is_logged_in,
            'reconnect_count': 0,
            'stats': self.stats.copy(),
            'config': {
                'connection_mode': 'mock',
                'mock_mode': True
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        if stats['start_time']:
            runtime = datetime.now() - stats['start_time']
            stats['runtime_seconds'] = runtime.total_seconds()
            
            if stats['runtime_seconds'] > 0:
                stats['market_data_rate'] = stats['market_data_count'] / stats['runtime_seconds']
                stats['transaction_rate'] = stats['transaction_count'] / stats['runtime_seconds']
                stats['order_detail_rate'] = stats['order_detail_count'] / stats['runtime_seconds']
        
        return stats
    
    def _data_generator(self):
        """数据生成线程"""
        self.logger.info("开始生成模拟数据...")
        
        while not self.stop_event.is_set():
            try:
                # 生成快照行情数据
                if random.random() < 0.8:  # 80%概率生成快照数据
                    self._generate_market_data()
                
                # 生成逐笔成交数据
                if random.random() < 0.3:  # 30%概率生成成交数据
                    self._generate_transaction_data()
                
                # 生成逐笔委托数据
                if random.random() < 0.4:  # 40%概率生成委托数据
                    self._generate_order_detail_data()
                
                # 控制数据生成频率
                time.sleep(random.uniform(0.1, 1.0))
                
            except Exception as e:
                self.logger.error(f"数据生成异常: {e}")
                time.sleep(1)
    
    def _generate_market_data(self):
        """生成模拟快照行情数据"""
        stock_code = random.choice(self.mock_stocks)
        stock_info = self.stock_prices[stock_code]
        
        # 模拟价格波动
        price_change = Decimal(str(random.uniform(-0.05, 0.05)))
        new_price = stock_info['price'] * (1 + price_change)
        stock_info['price'] = max(Decimal('0.01'), new_price)
        
        # 创建快照数据
        snapshot = Level2Snapshot(
            stock_code=stock_code,
            timestamp=datetime.now(),
            last_price=stock_info['price'],
            volume=stock_info['volume'] + random.randint(1000, 10000),
            amount=stock_info['price'] * (stock_info['volume'] + random.randint(1000, 10000)),
            
            # 模拟买卖五档
            bid_price_1=stock_info['price'] - Decimal('0.01'),
            bid_volume_1=random.randint(100, 10000),
            bid_price_2=stock_info['price'] - Decimal('0.02'),
            bid_volume_2=random.randint(100, 10000),
            bid_price_3=stock_info['price'] - Decimal('0.03'),
            bid_volume_3=random.randint(100, 10000),
            bid_price_4=stock_info['price'] - Decimal('0.04'),
            bid_volume_4=random.randint(100, 10000),
            bid_price_5=stock_info['price'] - Decimal('0.05'),
            bid_volume_5=random.randint(100, 10000),
            
            ask_price_1=stock_info['price'] + Decimal('0.01'),
            ask_volume_1=random.randint(100, 10000),
            ask_price_2=stock_info['price'] + Decimal('0.02'),
            ask_volume_2=random.randint(100, 10000),
            ask_price_3=stock_info['price'] + Decimal('0.03'),
            ask_volume_3=random.randint(100, 10000),
            ask_price_4=stock_info['price'] + Decimal('0.04'),
            ask_volume_4=random.randint(100, 10000),
            ask_price_5=stock_info['price'] + Decimal('0.05'),
            ask_volume_5=random.randint(100, 10000)
        )
        
        # 更新统计
        self.stats['market_data_count'] += 1
        self.stats['last_data_time'] = datetime.now()
        
        # 保存到数据库
        self._save_market_data(snapshot)
        
        # 调用回调函数
        for callback in self.data_callbacks['market_data']:
            try:
                callback(snapshot)
            except Exception as e:
                self.logger.error(f"快照行情回调失败: {e}")
    
    def _generate_transaction_data(self):
        """生成模拟逐笔成交数据"""
        stock_code = random.choice(self.mock_stocks)
        stock_info = self.stock_prices[stock_code]
        
        transaction = Level2Transaction(
            stock_code=stock_code,
            timestamp=datetime.now(),
            price=stock_info['price'],
            volume=random.randint(100, 5000),
            amount=stock_info['price'] * random.randint(100, 5000),
            buy_order_no=random.randint(100000, 999999),
            sell_order_no=random.randint(100000, 999999),
            trade_type='0'
        )
        
        # 更新统计
        self.stats['transaction_count'] += 1
        self.stats['last_data_time'] = datetime.now()
        
        # 保存到数据库
        self._save_transaction_data(transaction)
        
        # 调用回调函数
        for callback in self.data_callbacks['transaction']:
            try:
                callback(transaction)
            except Exception as e:
                self.logger.error(f"逐笔成交回调失败: {e}")
    
    def _generate_order_detail_data(self):
        """生成模拟逐笔委托数据"""
        stock_code = random.choice(self.mock_stocks)
        stock_info = self.stock_prices[stock_code]
        
        order_detail = Level2OrderDetail(
            stock_code=stock_code,
            timestamp=datetime.now(),
            order_no=random.randint(100000, 999999),
            price=stock_info['price'] + Decimal(str(random.uniform(-0.02, 0.02))),
            volume=random.randint(100, 5000),
            side=random.choice(['B', 'S']),
            order_type='0'
        )
        
        # 更新统计
        self.stats['order_detail_count'] += 1
        self.stats['last_data_time'] = datetime.now()
        
        # 保存到数据库
        self._save_order_detail_data(order_detail)
        
        # 调用回调函数
        for callback in self.data_callbacks['order_detail']:
            try:
                callback(order_detail)
            except Exception as e:
                self.logger.error(f"逐笔委托回调失败: {e}")
    
    def _save_market_data(self, snapshot: Level2Snapshot):
        """保存快照行情数据"""
        try:
            session = db_manager.get_session()
            session.add(snapshot)
            session.commit()
            session.close()
        except Exception as e:
            self.logger.error(f"保存快照数据失败: {e}")
    
    def _save_transaction_data(self, transaction: Level2Transaction):
        """保存逐笔成交数据"""
        try:
            session = db_manager.get_session()
            session.add(transaction)
            session.commit()
            session.close()
        except Exception as e:
            self.logger.error(f"保存成交数据失败: {e}")
    
    def _save_order_detail_data(self, order_detail: Level2OrderDetail):
        """保存逐笔委托数据"""
        try:
            session = db_manager.get_session()
            session.add(order_detail)
            session.commit()
            session.close()
        except Exception as e:
            self.logger.error(f"保存委托数据失败: {e}")


def create_mock_level2_receiver(config: Dict[str, Any]) -> MockLevel2DataReceiver:
    """创建模拟Level2数据接收器
    
    Args:
        config: 配置参数
        
    Returns:
        MockLevel2DataReceiver: 模拟接收器实例
    """
    return MockLevel2DataReceiver(config)
