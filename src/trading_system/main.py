"""
交易系统主入口模块
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .config.config_manager import ConfigManager
from .utils.logger import setup_logger


class TradingSystem:
    """股票自动交易系统主控制器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化交易系统
        
        Args:
            config_path: 配置文件路径，默认为 config/config.yaml
        """
        self.config_path = config_path or "config/config.yaml"
        self.config_manager = ConfigManager(self.config_path)
        self.config = self.config_manager.get_config()
        
        # 设置日志
        self.logger = setup_logger(self.config.get("logging", {}))
        
        # 系统状态
        self.is_running = False
        self.components = {}
        
        self.logger.info("交易系统初始化完成")
    
    async def start(self) -> bool:
        """启动交易系统"""
        try:
            self.logger.info("正在启动交易系统...")
            
            # 初始化各个组件
            await self._initialize_components()
            
            # 启动各个组件
            await self._start_components()
            
            self.is_running = True
            self.logger.info("交易系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"交易系统启动失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止交易系统"""
        try:
            self.logger.info("正在停止交易系统...")
            
            # 停止各个组件
            await self._stop_components()
            
            self.is_running = False
            self.logger.info("交易系统已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"交易系统停止失败: {e}")
            return False
    
    async def _initialize_components(self):
        """初始化系统组件"""
        # TODO: 初始化各个组件
        # - Level2数据接收器
        # - 历史评分引擎
        # - 股票池筛选器
        # - 买入策略引擎
        # - 监控系统
        pass
    
    async def _start_components(self):
        """启动系统组件"""
        # TODO: 启动各个组件
        pass
    
    async def _stop_components(self):
        """停止系统组件"""
        # TODO: 停止各个组件
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "is_running": self.is_running,
            "components": {name: comp.get_status() if hasattr(comp, 'get_status') else "unknown" 
                          for name, comp in self.components.items()},
            "config_path": self.config_path
        }


def main():
    """主函数入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="股票自动交易系统")
    parser.add_argument("--config", "-c", help="配置文件路径", default="config/config.yaml")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    
    args = parser.parse_args()
    
    # 创建交易系统实例
    trading_system = TradingSystem(args.config)
    
    async def run_system():
        """运行交易系统"""
        try:
            # 启动系统
            if await trading_system.start():
                # 保持运行
                while trading_system.is_running:
                    await asyncio.sleep(1)
            else:
                print("系统启动失败")
                return 1
                
        except KeyboardInterrupt:
            print("\n收到中断信号，正在停止系统...")
        except Exception as e:
            print(f"系统运行异常: {e}")
            return 1
        finally:
            await trading_system.stop()
        
        return 0
    
    # 运行系统
    exit_code = asyncio.run(run_system())
    exit(exit_code)


if __name__ == "__main__":
    main()
