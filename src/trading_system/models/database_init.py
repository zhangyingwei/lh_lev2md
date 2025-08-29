"""
数据库初始化脚本
"""

import logging
from pathlib import Path
from typing import Dict, Any
from .base import db_manager
from .data_lifecycle import DataLifecycleManager


def initialize_database(database_url: str = "sqlite:///data/trading_system.db") -> bool:
    """初始化数据库
    
    Args:
        database_url: 数据库连接URL
        
    Returns:
        bool: 初始化是否成功
    """
    logger = logging.getLogger('trading_system.database_init')
    
    try:
        # 确保数据目录存在
        if database_url.startswith('sqlite:///'):
            db_path = Path(database_url[10:])
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置数据库URL
        db_manager.database_url = database_url
        
        # 初始化数据库连接
        db_manager.initialize()
        
        logger.info("数据库初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def test_database_connection() -> Dict[str, Any]:
    """测试数据库连接
    
    Returns:
        Dict: 测试结果
    """
    logger = logging.getLogger('trading_system.database_test')
    
    try:
        session = db_manager.get_session()
        
        # 测试基本查询
        from sqlalchemy import text
        result = session.execute(text("SELECT 1 as test"))
        test_value = result.scalar()
        
        # 获取表列表
        result = session.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        session.close()
        
        test_result = {
            'connection_success': True,
            'test_query_result': test_value,
            'tables_created': tables,
            'table_count': len(tables)
        }
        
        logger.info(f"数据库连接测试成功，创建了{len(tables)}个表")
        return test_result
        
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return {
            'connection_success': False,
            'error': str(e)
        }


def setup_data_lifecycle(retention_days: int = 7) -> bool:
    """设置数据生命周期管理
    
    Args:
        retention_days: 数据保留天数
        
    Returns:
        bool: 设置是否成功
    """
    logger = logging.getLogger('trading_system.data_lifecycle_setup')
    
    try:
        # 创建数据生命周期管理器
        lifecycle_manager = DataLifecycleManager(retention_days=retention_days)
        
        # 获取数据库统计信息
        stats = lifecycle_manager.get_table_statistics()
        db_size = lifecycle_manager.get_database_size()
        
        logger.info(f"数据生命周期管理设置成功")
        logger.info(f"数据库大小: {db_size:.2f} MB")
        logger.info(f"表统计信息: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"数据生命周期管理设置失败: {e}")
        return False


def create_sample_data() -> bool:
    """创建示例数据
    
    Returns:
        bool: 创建是否成功
    """
    logger = logging.getLogger('trading_system.sample_data')
    
    try:
        from datetime import date, datetime
        from decimal import Decimal
        from .stock_data import StockInfo, DailyQuote
        
        session = db_manager.get_session()
        
        # 创建示例股票信息
        sample_stocks = [
            StockInfo(
                stock_code="000001",
                stock_name="平安银行",
                market="SZ",
                industry="银行",
                total_shares=Decimal("1943000"),
                float_shares=Decimal("1943000"),
                market_value=Decimal("25000000"),
                float_market_value=Decimal("25000000"),
                is_active=True
            ),
            StockInfo(
                stock_code="000002",
                stock_name="万科A",
                market="SZ",
                industry="房地产",
                total_shares=Decimal("1110000"),
                float_shares=Decimal("1110000"),
                market_value=Decimal("12000000"),
                float_market_value=Decimal("12000000"),
                is_active=True
            )
        ]
        
        # 添加股票信息
        for stock in sample_stocks:
            session.merge(stock)
        
        # 创建示例日线数据
        sample_quotes = [
            DailyQuote(
                stock_code="000001",
                trade_date=date.today(),
                pre_close=Decimal("12.50"),
                open_price=Decimal("12.55"),
                high_price=Decimal("12.80"),
                low_price=Decimal("12.45"),
                close_price=Decimal("12.75"),
                volume=50000000,
                amount=Decimal("635000000"),
                turnover_rate=Decimal("2.57"),
                change_amount=Decimal("0.25"),
                change_rate=Decimal("2.00"),
                amplitude=Decimal("2.80")
            )
        ]
        
        # 添加日线数据
        for quote in sample_quotes:
            session.merge(quote)
        
        session.commit()
        session.close()
        
        logger.info("示例数据创建成功")
        return True
        
    except Exception as e:
        logger.error(f"示例数据创建失败: {e}")
        return False


def main():
    """主函数"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger('trading_system.database_main')
    
    try:
        # 初始化数据库
        logger.info("开始初始化数据库...")
        if not initialize_database():
            logger.error("数据库初始化失败")
            sys.exit(1)
        
        # 测试数据库连接
        logger.info("测试数据库连接...")
        test_result = test_database_connection()
        if not test_result['connection_success']:
            logger.error("数据库连接测试失败")
            sys.exit(1)
        
        # 设置数据生命周期管理
        logger.info("设置数据生命周期管理...")
        if not setup_data_lifecycle():
            logger.error("数据生命周期管理设置失败")
            sys.exit(1)
        
        # 创建示例数据
        logger.info("创建示例数据...")
        if not create_sample_data():
            logger.error("示例数据创建失败")
            sys.exit(1)
        
        logger.info("数据库初始化完成！")
        
    except Exception as e:
        logger.error(f"数据库初始化过程中发生异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
