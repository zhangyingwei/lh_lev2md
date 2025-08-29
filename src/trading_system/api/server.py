"""
API服务器启动脚本

提供命令行启动API服务器的功能
"""

import asyncio
import argparse
import signal
import sys
from pathlib import Path

from .web_api import create_web_api
from ..utils.logger import setup_logger


class APIServer:
    """API服务器管理器"""
    
    def __init__(self, config_path: str, host: str = "0.0.0.0", port: int = 8000):
        """初始化服务器
        
        Args:
            config_path: 配置文件路径
            host: 监听地址
            port: 监听端口
        """
        self.config_path = config_path
        self.host = host
        self.port = port
        
        # 设置日志
        self.logger = setup_logger({})
        
        # 创建API实例
        self.api = create_web_api(config_path)
        
        # 服务器运行标志
        self.running = False
        
        self.logger.info("API服务器管理器初始化完成")
    
    async def start(self):
        """启动服务器"""
        try:
            self.running = True
            self.logger.info(f"启动API服务器: http://{self.host}:{self.port}")
            
            # 注册信号处理器
            self._setup_signal_handlers()
            
            # 启动服务器
            await self.api.start_server(self.host, self.port)
            
        except Exception as e:
            self.logger.error(f"API服务器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止服务器"""
        try:
            self.running = False
            self.logger.info("停止API服务器...")
            
            # 这里可以添加优雅关闭逻辑
            
        except Exception as e:
            self.logger.error(f"API服务器停止失败: {e}")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，准备关闭服务器...")
            self.running = False
            # 创建停止任务
            asyncio.create_task(self.stop())
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="量化交易系统API服务器")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--auto-start", action="store_true", help="自动启动交易系统")
    
    args = parser.parse_args()
    
    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置文件不存在: {config_path}")
        return 1
    
    try:
        # 创建服务器
        server = APIServer(args.config, args.host, args.port)
        
        # 如果需要自动启动交易系统
        if args.auto_start:
            server.logger.info("自动启动交易系统...")
            # 这里可以添加自动启动逻辑
        
        # 启动服务器
        await server.start()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n服务器被用户中断")
        return 1
    except Exception as e:
        print(f"服务器异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
