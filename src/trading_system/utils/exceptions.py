"""
异常处理模块
"""

from typing import Dict, Any, Optional


class TradingSystemException(Exception):
    """交易系统基础异常"""
    
    def __init__(self, message: str, error_code: int = 500, details: Optional[Dict[str, Any]] = None):
        """初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class Level2ConnectionException(TradingSystemException):
    """Level2连接异常"""
    
    def __init__(self, message: str, reason_code: Optional[int] = None):
        """初始化Level2连接异常
        
        Args:
            message: 错误消息
            reason_code: Level2断开原因码
        """
        super().__init__(message, 1001, {'reason_code': reason_code})


class DataValidationException(TradingSystemException):
    """数据验证异常"""
    
    def __init__(self, message: str, field_name: Optional[str] = None, field_value: Any = None):
        """初始化数据验证异常
        
        Args:
            message: 错误消息
            field_name: 字段名
            field_value: 字段值
        """
        super().__init__(message, 1002, {
            'field_name': field_name,
            'field_value': field_value
        })


class CalculationException(TradingSystemException):
    """计算异常"""
    
    def __init__(self, message: str, calculation_type: Optional[str] = None):
        """初始化计算异常
        
        Args:
            message: 错误消息
            calculation_type: 计算类型
        """
        super().__init__(message, 1003, {'calculation_type': calculation_type})


class StrategyException(TradingSystemException):
    """策略执行异常"""

    def __init__(self, message: str, strategy_name: Optional[str] = None):
        """初始化策略异常

        Args:
            message: 错误消息
            strategy_name: 策略名称
        """
        super().__init__(message, 1004, {'strategy_name': strategy_name})


class ValidationException(TradingSystemException):
    """验证异常"""

    def __init__(self, message: str, validation_type: Optional[str] = None):
        """初始化验证异常

        Args:
            message: 错误消息
            validation_type: 验证类型
        """
        super().__init__(message, 1005, {'validation_type': validation_type})


def exception_handler(exception_types: tuple = (Exception,), 
                     default_return: Any = None,
                     log_error: bool = True):
    """异常处理装饰器
    
    Args:
        exception_types: 要捕获的异常类型
        default_return: 默认返回值
        log_error: 是否记录错误日志
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                if log_error:
                    import logging
                    logger = logging.getLogger('trading_system')
                    logger.error(f"函数 {func.__name__} 执行异常: {e}", exc_info=True)
                
                if isinstance(e, TradingSystemException):
                    # 记录业务异常详情
                    logger.warning(f"业务异常 - 错误码: {e.error_code}, 详情: {e.details}")
                
                return default_return
        return wrapper
    return decorator


def retry_on_exception(max_attempts: int = 3, 
                      delay: float = 1.0,
                      backoff_factor: float = 2.0,
                      exception_types: tuple = (Exception,)):
    """重试机制装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子
        exception_types: 要重试的异常类型
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            import logging
            
            logger = logging.getLogger('trading_system')
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"函数 {func.__name__} 重试 {max_attempts} 次后仍然失败")
                        raise e
                    
                    logger.warning(f"函数 {func.__name__} 第 {attempt} 次执行失败，{current_delay}秒后重试")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
        return wrapper
    return decorator
