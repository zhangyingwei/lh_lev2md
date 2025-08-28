#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
实时数据解析器

功能说明：
1. 解析Level2推送的各种数据格式
2. 实现数据格式标准化和验证
3. 支持多种数据类型的解析转换
4. 数据字段映射和类型转换

作者：AI Agent Development Team
版本：v1.0.0
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from enum import Enum
import struct


class DataType(Enum):
    """数据类型枚举"""
    MARKET_DATA = "market_data"          # 快照行情
    TRANSACTION = "transaction"          # 逐笔成交
    ORDER_DETAIL = "order_detail"        # 逐笔委托
    INDEX = "index"                      # 指数行情
    XTS_MARKET_DATA = "xts_market_data"  # XTS新债快照
    XTS_TICK = "xts_tick"               # XTS新债逐笔
    NGTS_TICK = "ngts_tick"             # NGTS合流逐笔


class DataParser:
    """实时数据解析器
    
    负责解析Level2各种类型的原始数据，转换为标准化格式
    """
    
    def __init__(self, config: Dict):
        """
        初始化数据解析器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 解析统计
        self.stats = {
            'total_parsed': 0,
            'parse_errors': 0,
            'validation_errors': 0,
            'last_parse_time': None,
            'parse_latency': [],
            'data_type_counts': {}
        }
        
        # 字段映射配置
        self.field_mappings = self._init_field_mappings()
        
        # 数据验证规则
        self.validation_rules = self._init_validation_rules()
        
        self.logger.info("DataParser初始化完成")
    
    def _init_field_mappings(self) -> Dict[str, Dict[str, str]]:
        """初始化字段映射配置"""
        return {
            'market_data': {
                'SecurityID': 'stock_code',
                'ExchangeID': 'exchange_id',
                'DataTimeStamp': 'timestamp',
                'LastPrice': 'last_price',
                'PreClosePrice': 'pre_close_price',
                'OpenPrice': 'open_price',
                'HighestPrice': 'high_price',
                'LowestPrice': 'low_price',
                'TotalVolumeTrade': 'volume',
                'TotalValueTrade': 'amount',
                'BidPrice1': 'bid_price_1',
                'BidPrice2': 'bid_price_2',
                'BidPrice3': 'bid_price_3',
                'BidPrice4': 'bid_price_4',
                'BidPrice5': 'bid_price_5',
                'BidPrice6': 'bid_price_6',
                'BidPrice7': 'bid_price_7',
                'BidPrice8': 'bid_price_8',
                'BidPrice9': 'bid_price_9',
                'BidPrice10': 'bid_price_10',
                'AskPrice1': 'ask_price_1',
                'AskPrice2': 'ask_price_2',
                'AskPrice3': 'ask_price_3',
                'AskPrice4': 'ask_price_4',
                'AskPrice5': 'ask_price_5',
                'AskPrice6': 'ask_price_6',
                'AskPrice7': 'ask_price_7',
                'AskPrice8': 'ask_price_8',
                'AskPrice9': 'ask_price_9',
                'AskPrice10': 'ask_price_10',
                'BidVolume1': 'bid_volume_1',
                'BidVolume2': 'bid_volume_2',
                'BidVolume3': 'bid_volume_3',
                'BidVolume4': 'bid_volume_4',
                'BidVolume5': 'bid_volume_5',
                'BidVolume6': 'bid_volume_6',
                'BidVolume7': 'bid_volume_7',
                'BidVolume8': 'bid_volume_8',
                'BidVolume9': 'bid_volume_9',
                'BidVolume10': 'bid_volume_10',
                'AskVolume1': 'ask_volume_1',
                'AskVolume2': 'ask_volume_2',
                'AskVolume3': 'ask_volume_3',
                'AskVolume4': 'ask_volume_4',
                'AskVolume5': 'ask_volume_5',
                'AskVolume6': 'ask_volume_6',
                'AskVolume7': 'ask_volume_7',
                'AskVolume8': 'ask_volume_8',
                'AskVolume9': 'ask_volume_9',
                'AskVolume10': 'ask_volume_10',
                'UpperLimitPrice': 'upper_limit_price',
                'LowerLimitPrice': 'lower_limit_price',
                'PERatio1': 'pe_ratio_1',
                'PERatio2': 'pe_ratio_2'
            },
            'transaction': {
                'SecurityID': 'stock_code',
                'ExchangeID': 'exchange_id',
                'TradeTime': 'trade_time',
                'TradePrice': 'trade_price',
                'TradeVolume': 'trade_volume',
                'ExecType': 'exec_type',
                'MainSeq': 'main_seq',
                'SubSeq': 'sub_seq',
                'BuyNo': 'buy_no',
                'SellNo': 'sell_no',
                'TradeBSFlag': 'trade_bs_flag'
            },
            'order_detail': {
                'SecurityID': 'stock_code',
                'ExchangeID': 'exchange_id',
                'OrderTime': 'order_time',
                'Price': 'price',
                'Volume': 'volume',
                'OrderType': 'order_type',
                'MainSeq': 'main_seq',
                'SubSeq': 'sub_seq',
                'Side': 'side'
            }
        }
    
    def _init_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化数据验证规则"""
        return {
            'market_data': {
                'required_fields': ['stock_code', 'exchange_id', 'timestamp', 'last_price'],
                'price_fields': ['last_price', 'pre_close_price', 'open_price', 'high_price', 'low_price'],
                'volume_fields': ['volume'],
                'amount_fields': ['amount'],
                'price_range': (0.01, 10000.0),  # 价格合理范围
                'volume_range': (0, 1000000000),  # 成交量合理范围
            },
            'transaction': {
                'required_fields': ['stock_code', 'exchange_id', 'trade_time', 'trade_price', 'trade_volume'],
                'price_fields': ['trade_price'],
                'volume_fields': ['trade_volume'],
                'price_range': (0.01, 10000.0),
                'volume_range': (100, 100000000),  # 单笔成交量范围
            },
            'order_detail': {
                'required_fields': ['stock_code', 'exchange_id', 'order_time', 'price', 'volume'],
                'price_fields': ['price'],
                'volume_fields': ['volume'],
                'price_range': (0.01, 10000.0),
                'volume_range': (100, 100000000),  # 单笔委托量范围
            }
        }
    
    def parse_market_data(self, raw_data: Dict, 
                         first_level_buy_num: int = 0,
                         first_level_buy_volumes: List[int] = None,
                         first_level_sell_num: int = 0,
                         first_level_sell_volumes: List[int] = None) -> Optional[Dict[str, Any]]:
        """
        解析快照行情数据
        
        Args:
            raw_data: 原始数据字典
            first_level_buy_num: 一档买单笔数
            first_level_buy_volumes: 一档买委托量列表
            first_level_sell_num: 一档卖单笔数
            first_level_sell_volumes: 一档卖委托量列表
            
        Returns:
            Dict: 标准化的快照行情数据
        """
        try:
            start_time = time.perf_counter()
            
            # 字段映射
            parsed_data = self._map_fields(raw_data, 'market_data')
            if not parsed_data:
                return None
            
            # 数据类型转换
            parsed_data = self._convert_data_types(parsed_data, 'market_data')
            
            # 添加额外信息
            parsed_data['data_type'] = DataType.MARKET_DATA.value
            parsed_data['parse_time'] = datetime.now()
            
            # 处理一档委托信息
            if first_level_buy_num > 0 and first_level_buy_volumes:
                parsed_data['first_level_buy_num'] = first_level_buy_num
                parsed_data['first_level_buy_volumes'] = first_level_buy_volumes[:first_level_buy_num]
            
            if first_level_sell_num > 0 and first_level_sell_volumes:
                parsed_data['first_level_sell_num'] = first_level_sell_num
                parsed_data['first_level_sell_volumes'] = first_level_sell_volumes[:first_level_sell_num]
            
            # 计算衍生字段
            parsed_data = self._calculate_derived_fields(parsed_data, 'market_data')
            
            # 数据验证
            if not self._validate_data(parsed_data, 'market_data'):
                return None
            
            # 更新统计
            self._update_parse_stats('market_data', start_time)
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"解析快照行情数据异常: {e}", exc_info=True)
            self.stats['parse_errors'] += 1
            return None

    def parse_transaction(self, raw_data: Dict) -> Optional[Dict[str, Any]]:
        """
        解析逐笔成交数据

        Args:
            raw_data: 原始数据字典

        Returns:
            Dict: 标准化的逐笔成交数据
        """
        try:
            start_time = time.perf_counter()

            # 字段映射
            parsed_data = self._map_fields(raw_data, 'transaction')
            if not parsed_data:
                return None

            # 数据类型转换
            parsed_data = self._convert_data_types(parsed_data, 'transaction')

            # 添加额外信息
            parsed_data['data_type'] = DataType.TRANSACTION.value
            parsed_data['parse_time'] = datetime.now()

            # 计算衍生字段
            parsed_data = self._calculate_derived_fields(parsed_data, 'transaction')

            # 数据验证
            if not self._validate_data(parsed_data, 'transaction'):
                return None

            # 更新统计
            self._update_parse_stats('transaction', start_time)

            return parsed_data

        except Exception as e:
            self.logger.error(f"解析逐笔成交数据异常: {e}", exc_info=True)
            self.stats['parse_errors'] += 1
            return None

    def parse_order_detail(self, raw_data: Dict) -> Optional[Dict[str, Any]]:
        """
        解析逐笔委托数据

        Args:
            raw_data: 原始数据字典

        Returns:
            Dict: 标准化的逐笔委托数据
        """
        try:
            start_time = time.perf_counter()

            # 字段映射
            parsed_data = self._map_fields(raw_data, 'order_detail')
            if not parsed_data:
                return None

            # 数据类型转换
            parsed_data = self._convert_data_types(parsed_data, 'order_detail')

            # 添加额外信息
            parsed_data['data_type'] = DataType.ORDER_DETAIL.value
            parsed_data['parse_time'] = datetime.now()

            # 计算衍生字段
            parsed_data = self._calculate_derived_fields(parsed_data, 'order_detail')

            # 数据验证
            if not self._validate_data(parsed_data, 'order_detail'):
                return None

            # 更新统计
            self._update_parse_stats('order_detail', start_time)

            return parsed_data

        except Exception as e:
            self.logger.error(f"解析逐笔委托数据异常: {e}", exc_info=True)
            self.stats['parse_errors'] += 1
            return None

    def _map_fields(self, raw_data: Dict, data_type: str) -> Optional[Dict[str, Any]]:
        """
        字段映射

        Args:
            raw_data: 原始数据
            data_type: 数据类型

        Returns:
            Dict: 映射后的数据
        """
        try:
            if data_type not in self.field_mappings:
                self.logger.error(f"不支持的数据类型: {data_type}")
                return None

            mapping = self.field_mappings[data_type]
            parsed_data = {}

            for raw_field, std_field in mapping.items():
                if raw_field in raw_data:
                    value = raw_data[raw_field]

                    # 处理字节字符串
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8').strip()
                        except UnicodeDecodeError:
                            value = value.decode('gbk', errors='ignore').strip()

                    parsed_data[std_field] = value
                else:
                    # 对于必需字段，记录警告
                    rules = self.validation_rules.get(data_type, {})
                    required_fields = rules.get('required_fields', [])
                    if std_field in required_fields:
                        self.logger.warning(f"缺少必需字段: {raw_field} -> {std_field}")

            return parsed_data

        except Exception as e:
            self.logger.error(f"字段映射异常: {e}", exc_info=True)
            return None

    def _convert_data_types(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        数据类型转换

        Args:
            data: 待转换数据
            data_type: 数据类型

        Returns:
            Dict: 转换后的数据
        """
        try:
            rules = self.validation_rules.get(data_type, {})
            price_fields = rules.get('price_fields', [])
            volume_fields = rules.get('volume_fields', [])
            amount_fields = rules.get('amount_fields', [])

            for field, value in data.items():
                if value is None or value == '':
                    continue

                try:
                    # 价格字段转换为Decimal
                    if field in price_fields:
                        if isinstance(value, (int, float)):
                            data[field] = Decimal(str(value))
                        elif isinstance(value, str):
                            data[field] = Decimal(value) if value != '0' else Decimal('0')
                        else:
                            data[field] = Decimal(str(value))

                    # 成交量/委托量字段转换为整数
                    elif field in volume_fields:
                        data[field] = int(float(value)) if value != 0 else 0

                    # 成交额字段转换为Decimal
                    elif field in amount_fields:
                        data[field] = Decimal(str(value)) if value != 0 else Decimal('0')

                    # 时间字段处理
                    elif 'time' in field.lower():
                        data[field] = self._parse_time_field(value)

                    # 序号字段转换为整数
                    elif 'seq' in field.lower():
                        data[field] = int(value) if value != 0 else 0

                    # 其他数值字段
                    elif isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                        if '.' in value:
                            data[field] = float(value)
                        else:
                            data[field] = int(value)

                except (ValueError, TypeError, InvalidOperation) as e:
                    self.logger.warning(f"字段类型转换失败: {field}={value}, 错误: {e}")
                    # 保持原值
                    pass

            return data

        except Exception as e:
            self.logger.error(f"数据类型转换异常: {e}", exc_info=True)
            return data

    def _parse_time_field(self, time_value: Union[str, int, float]) -> Optional[datetime]:
        """
        解析时间字段

        Args:
            time_value: 时间值

        Returns:
            datetime: 解析后的时间对象
        """
        try:
            if isinstance(time_value, str):
                # 处理字符串时间格式
                if len(time_value) == 8:  # HHMMSSFF格式
                    hour = int(time_value[:2])
                    minute = int(time_value[2:4])
                    second = int(time_value[4:6])
                    microsecond = int(time_value[6:8]) * 10000

                    today = date.today()
                    return datetime.combine(today, datetime.min.time().replace(
                        hour=hour, minute=minute, second=second, microsecond=microsecond
                    ))
                elif len(time_value) == 6:  # HHMMSS格式
                    hour = int(time_value[:2])
                    minute = int(time_value[2:4])
                    second = int(time_value[4:6])

                    today = date.today()
                    return datetime.combine(today, datetime.min.time().replace(
                        hour=hour, minute=minute, second=second
                    ))
                else:
                    # 尝试标准时间格式解析
                    return datetime.fromisoformat(time_value)

            elif isinstance(time_value, (int, float)):
                # 处理时间戳
                if time_value > 1000000000000:  # 毫秒时间戳
                    return datetime.fromtimestamp(time_value / 1000)
                else:  # 秒时间戳
                    return datetime.fromtimestamp(time_value)

            return None

        except (ValueError, TypeError) as e:
            self.logger.warning(f"时间字段解析失败: {time_value}, 错误: {e}")
            return None

    def _calculate_derived_fields(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        计算衍生字段

        Args:
            data: 数据字典
            data_type: 数据类型

        Returns:
            Dict: 添加衍生字段后的数据
        """
        try:
            if data_type == 'market_data':
                # 计算涨跌幅
                if 'last_price' in data and 'pre_close_price' in data:
                    last_price = data['last_price']
                    pre_close = data['pre_close_price']

                    if pre_close and pre_close > 0:
                        change = last_price - pre_close
                        change_pct = (change / pre_close) * 100

                        data['price_change'] = change
                        data['change_percent'] = round(change_pct, 2)

                # 计算振幅
                if all(k in data for k in ['high_price', 'low_price', 'pre_close_price']):
                    high_price = data['high_price']
                    low_price = data['low_price']
                    pre_close = data['pre_close_price']

                    if pre_close and pre_close > 0:
                        amplitude = ((high_price - low_price) / pre_close) * 100
                        data['amplitude'] = round(amplitude, 2)

                # 计算换手率（需要流通股本数据，这里先预留）
                if 'volume' in data:
                    # data['turnover_rate'] = 计算换手率的逻辑
                    pass

                # 整理买卖盘数据
                bid_prices = []
                bid_volumes = []
                ask_prices = []
                ask_volumes = []

                for i in range(1, 11):
                    bid_price_key = f'bid_price_{i}'
                    bid_volume_key = f'bid_volume_{i}'
                    ask_price_key = f'ask_price_{i}'
                    ask_volume_key = f'ask_volume_{i}'

                    if bid_price_key in data and data[bid_price_key]:
                        bid_prices.append(data[bid_price_key])
                        bid_volumes.append(data.get(bid_volume_key, 0))

                    if ask_price_key in data and data[ask_price_key]:
                        ask_prices.append(data[ask_price_key])
                        ask_volumes.append(data.get(ask_volume_key, 0))

                data['bid_prices'] = bid_prices
                data['bid_volumes'] = bid_volumes
                data['ask_prices'] = ask_prices
                data['ask_volumes'] = ask_volumes

            elif data_type == 'transaction':
                # 计算成交金额
                if 'trade_price' in data and 'trade_volume' in data:
                    trade_amount = data['trade_price'] * data['trade_volume']
                    data['trade_amount'] = trade_amount

                # 解析买卖方向
                if 'trade_bs_flag' in data:
                    bs_flag = data['trade_bs_flag']
                    if bs_flag == 'B':
                        data['trade_direction'] = 'buy'
                    elif bs_flag == 'S':
                        data['trade_direction'] = 'sell'
                    else:
                        data['trade_direction'] = 'unknown'

            elif data_type == 'order_detail':
                # 计算委托金额
                if 'price' in data and 'volume' in data:
                    order_amount = data['price'] * data['volume']
                    data['order_amount'] = order_amount

                # 解析委托方向
                if 'side' in data:
                    side = data['side']
                    if side == '1' or side == 'B':
                        data['order_direction'] = 'buy'
                    elif side == '2' or side == 'S':
                        data['order_direction'] = 'sell'
                    else:
                        data['order_direction'] = 'unknown'

            return data

        except Exception as e:
            self.logger.error(f"计算衍生字段异常: {e}", exc_info=True)
            return data

    def _validate_data(self, data: Dict[str, Any], data_type: str) -> bool:
        """
        数据验证

        Args:
            data: 待验证数据
            data_type: 数据类型

        Returns:
            bool: 验证是否通过
        """
        try:
            rules = self.validation_rules.get(data_type, {})

            # 检查必需字段
            required_fields = rules.get('required_fields', [])
            for field in required_fields:
                if field not in data or data[field] is None:
                    self.logger.warning(f"缺少必需字段: {field}")
                    self.stats['validation_errors'] += 1
                    return False

            # 检查价格字段合理性
            price_fields = rules.get('price_fields', [])
            price_range = rules.get('price_range', (0, float('inf')))

            for field in price_fields:
                if field in data and data[field] is not None:
                    price = float(data[field])
                    if not (price_range[0] <= price <= price_range[1]):
                        self.logger.warning(
                            f"价格字段超出合理范围: {field}={price}, "
                            f"合理范围: {price_range}"
                        )
                        self.stats['validation_errors'] += 1
                        return False

            # 检查成交量字段合理性
            volume_fields = rules.get('volume_fields', [])
            volume_range = rules.get('volume_range', (0, float('inf')))

            for field in volume_fields:
                if field in data and data[field] is not None:
                    volume = int(data[field])
                    if not (volume_range[0] <= volume <= volume_range[1]):
                        self.logger.warning(
                            f"成交量字段超出合理范围: {field}={volume}, "
                            f"合理范围: {volume_range}"
                        )
                        self.stats['validation_errors'] += 1
                        return False

            # 特定数据类型的额外验证
            if data_type == 'market_data':
                # 验证买卖盘价格递减/递增关系
                if not self._validate_order_book(data):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"数据验证异常: {e}", exc_info=True)
            self.stats['validation_errors'] += 1
            return False

    def _validate_order_book(self, data: Dict[str, Any]) -> bool:
        """
        验证买卖盘数据的合理性

        Args:
            data: 快照行情数据

        Returns:
            bool: 验证是否通过
        """
        try:
            # 检查买盘价格递减
            bid_prices = data.get('bid_prices', [])
            for i in range(1, len(bid_prices)):
                if bid_prices[i] > bid_prices[i-1]:
                    self.logger.warning(f"买盘价格顺序异常: {bid_prices}")
                    return False

            # 检查卖盘价格递增
            ask_prices = data.get('ask_prices', [])
            for i in range(1, len(ask_prices)):
                if ask_prices[i] < ask_prices[i-1]:
                    self.logger.warning(f"卖盘价格顺序异常: {ask_prices}")
                    return False

            # 检查买一价 <= 卖一价
            if bid_prices and ask_prices:
                if bid_prices[0] > ask_prices[0]:
                    self.logger.warning(
                        f"买一价高于卖一价: 买一={bid_prices[0]}, 卖一={ask_prices[0]}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"买卖盘验证异常: {e}", exc_info=True)
            return False

    def _update_parse_stats(self, data_type: str, start_time: float):
        """
        更新解析统计信息

        Args:
            data_type: 数据类型
            start_time: 开始时间
        """
        try:
            # 计算解析延迟
            parse_latency = (time.perf_counter() - start_time) * 1000  # 毫秒

            # 更新统计
            self.stats['total_parsed'] += 1
            self.stats['last_parse_time'] = datetime.now()
            self.stats['parse_latency'].append(parse_latency)

            # 保持延迟统计数组大小
            if len(self.stats['parse_latency']) > 1000:
                self.stats['parse_latency'] = self.stats['parse_latency'][-1000:]

            # 更新数据类型统计
            if data_type not in self.stats['data_type_counts']:
                self.stats['data_type_counts'][data_type] = 0
            self.stats['data_type_counts'][data_type] += 1

        except Exception as e:
            self.logger.error(f"更新解析统计异常: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取解析统计信息

        Returns:
            Dict: 统计信息
        """
        try:
            stats = self.stats.copy()

            # 计算平均延迟
            if self.stats['parse_latency']:
                stats['avg_latency_ms'] = sum(self.stats['parse_latency']) / len(self.stats['parse_latency'])
                stats['max_latency_ms'] = max(self.stats['parse_latency'])
                stats['min_latency_ms'] = min(self.stats['parse_latency'])
            else:
                stats['avg_latency_ms'] = 0
                stats['max_latency_ms'] = 0
                stats['min_latency_ms'] = 0

            # 计算成功率
            total_attempts = stats['total_parsed'] + stats['parse_errors'] + stats['validation_errors']
            if total_attempts > 0:
                stats['success_rate'] = (stats['total_parsed'] / total_attempts) * 100
            else:
                stats['success_rate'] = 0

            return stats

        except Exception as e:
            self.logger.error(f"获取统计信息异常: {e}", exc_info=True)
            return {}

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_parsed': 0,
            'parse_errors': 0,
            'validation_errors': 0,
            'last_parse_time': None,
            'parse_latency': [],
            'data_type_counts': {}
        }
        self.logger.info("解析统计信息已重置")
