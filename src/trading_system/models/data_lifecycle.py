"""
数据生命周期管理模块
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy import text
from .base import db_manager


class DataLifecycleManager:
    """1周数据生命周期管理器"""
    
    def __init__(self, retention_days: int = 7):
        """初始化数据生命周期管理器
        
        Args:
            retention_days: 数据保留天数，默认7天
        """
        self.retention_days = retention_days
        self.logger = logging.getLogger('trading_system.data_lifecycle')
        
    def cleanup_old_data(self) -> Dict[str, int]:
        """清理超过保留期的历史数据
        
        Returns:
            Dict: 清理结果统计
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        cutoff_date_only = cutoff_date.date()
        
        cleanup_stats = {
            'level2_snapshots': 0,
            'level2_transactions': 0,
            'level2_order_details': 0,
            'historical_scores': 0,
            'trading_signals': 0,
            'stock_pool_results': 0,
            'system_metrics': 0
        }
        
        try:
            session = db_manager.get_session()
            
            # 清理Level2快照数据
            result = session.execute(text("""
                DELETE FROM level2_snapshots 
                WHERE created_at < :cutoff_date
            """), {'cutoff_date': cutoff_date})
            cleanup_stats['level2_snapshots'] = result.rowcount
            
            # 清理Level2逐笔成交数据
            result = session.execute(text("""
                DELETE FROM level2_transactions 
                WHERE created_at < :cutoff_date
            """), {'cutoff_date': cutoff_date})
            cleanup_stats['level2_transactions'] = result.rowcount
            
            # 清理Level2逐笔委托数据
            result = session.execute(text("""
                DELETE FROM level2_order_details 
                WHERE created_at < :cutoff_date
            """), {'cutoff_date': cutoff_date})
            cleanup_stats['level2_order_details'] = result.rowcount
            
            # 清理历史评分数据
            result = session.execute(text("""
                DELETE FROM historical_scores 
                WHERE trade_date < :cutoff_date
            """), {'cutoff_date': cutoff_date_only})
            cleanup_stats['historical_scores'] = result.rowcount
            
            # 清理交易信号数据
            result = session.execute(text("""
                DELETE FROM trading_signals 
                WHERE created_at < :cutoff_date
            """), {'cutoff_date': cutoff_date})
            cleanup_stats['trading_signals'] = result.rowcount
            
            # 清理股票池结果数据
            result = session.execute(text("""
                DELETE FROM stock_pool_results 
                WHERE trade_date < :cutoff_date
            """), {'cutoff_date': cutoff_date_only})
            cleanup_stats['stock_pool_results'] = result.rowcount
            
            # 清理系统监控数据
            result = session.execute(text("""
                DELETE FROM system_metrics 
                WHERE created_at < :cutoff_date
            """), {'cutoff_date': cutoff_date})
            cleanup_stats['system_metrics'] = result.rowcount
            
            # 提交事务
            session.commit()
            
            # 执行VACUUM优化数据库
            session.execute(text("VACUUM"))
            session.commit()
            
            total_deleted = sum(cleanup_stats.values())
            self.logger.info(f"数据清理完成，删除{cutoff_date}之前的数据，总计删除{total_deleted}条记录")
            
            return cleanup_stats
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"数据清理失败: {e}")
            raise
        finally:
            session.close()
    
    def get_database_size(self) -> float:
        """获取数据库文件大小（MB）
        
        Returns:
            float: 数据库文件大小（MB）
        """
        try:
            # 从数据库URL中提取文件路径
            db_url = db_manager.database_url
            if db_url.startswith('sqlite:///'):
                db_path = Path(db_url[10:])  # 去掉 'sqlite:///' 前缀
                if db_path.exists():
                    return db_path.stat().st_size / (1024 * 1024)
            return 0.0
        except Exception as e:
            self.logger.error(f"获取数据库大小失败: {e}")
            return 0.0
    
    def get_table_statistics(self) -> Dict[str, Dict[str, Any]]:
        """获取各表的统计信息
        
        Returns:
            Dict: 表统计信息
        """
        tables = [
            'stock_info', 'daily_quote', 'level2_snapshots',
            'level2_transactions', 'level2_order_details',
            'historical_scores', 'stock_pool_results',
            'trading_signals', 'system_metrics'
        ]
        
        stats = {}
        
        try:
            session = db_manager.get_session()
            
            for table in tables:
                # 获取记录数
                result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                
                # 获取最新记录时间
                latest_time = None
                if table in ['level2_snapshots', 'level2_transactions', 'level2_order_details', 
                           'trading_signals', 'system_metrics']:
                    result = session.execute(text(f"SELECT MAX(created_at) FROM {table}"))
                    latest_time = result.scalar()
                elif table in ['historical_scores', 'stock_pool_results']:
                    result = session.execute(text(f"SELECT MAX(trade_date) FROM {table}"))
                    latest_time = result.scalar()
                elif table == 'daily_quote':
                    result = session.execute(text(f"SELECT MAX(trade_date) FROM {table}"))
                    latest_time = result.scalar()
                
                stats[table] = {
                    'count': count,
                    'latest_time': latest_time.isoformat() if latest_time else None
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取表统计信息失败: {e}")
            return {}
        finally:
            session.close()
    
    def schedule_cleanup(self):
        """定时清理任务（每日凌晨2点执行）"""
        import schedule
        import time
        import threading
        
        def cleanup_job():
            """清理任务"""
            try:
                self.logger.info("开始执行定时数据清理任务")
                stats = self.cleanup_old_data()
                self.logger.info(f"定时清理完成: {stats}")
            except Exception as e:
                self.logger.error(f"定时清理任务失败: {e}")
        
        # 设置定时任务
        schedule.every().day.at("02:00").do(cleanup_job)
        
        def run_scheduler():
            """运行调度器"""
            while True:
                schedule.run_pending()
                time.sleep(3600)  # 每小时检查一次
        
        # 在后台线程中运行调度器
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        self.logger.info("数据清理定时任务已启动，每日凌晨2点执行")
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """备份数据库
        
        Args:
            backup_path: 备份文件路径，默认为data/backup/目录
            
        Returns:
            str: 备份文件路径
        """
        if backup_path is None:
            backup_dir = Path("data/backup")
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"trading_system_backup_{timestamp}.db"
        
        try:
            # 获取源数据库路径
            db_url = db_manager.database_url
            if db_url.startswith('sqlite:///'):
                source_path = Path(db_url[10:])
                
                # 执行备份
                import shutil
                shutil.copy2(source_path, backup_path)
                
                self.logger.info(f"数据库备份完成: {backup_path}")
                return str(backup_path)
            else:
                raise ValueError("只支持SQLite数据库备份")
                
        except Exception as e:
            self.logger.error(f"数据库备份失败: {e}")
            raise
