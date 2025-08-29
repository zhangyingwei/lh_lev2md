#!/usr/bin/env python3
"""
量化交易系统启动脚本

提供简单易用的系统启动功能
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from trading_system.services import create_trading_service
from trading_system.api import create_web_api
from trading_system.web import create_static_server


async def start_trading_service(config_path: str):
    """启动交易服务
    
    Args:
        config_path: 配置文件路径
    """
    print("启动量化交易服务...")
    
    # 创建交易服务
    service = create_trading_service(config_path)
    
    try:
        # 启动服务
        if await service.start():
            print("✅ 交易服务启动成功")
            
            # 订阅一些测试股票
            test_stocks = ['000001', '000002', '600000', '600036', '600519']
            await service.subscribe_stocks(test_stocks)
            print(f"✅ 已订阅测试股票: {test_stocks}")
            
            # 保持运行
            print("系统运行中，按 Ctrl+C 停止...")
            try:
                while True:
                    await asyncio.sleep(10)
                    
                    # 显示系统状态
                    stats = service.get_system_statistics()
                    print(f"系统状态: 运行中, 事件数: {stats['data_statistics']['total_events_detected']}, "
                          f"推荐数: {stats['data_statistics']['total_recommendations']}")
                    
            except KeyboardInterrupt:
                print("\n收到停止信号...")
        else:
            print("❌ 交易服务启动失败")
            return False
            
    finally:
        # 停止服务
        await service.stop()
        print("✅ 交易服务已停止")
    
    return True


async def start_api_server(config_path: str, host: str = "0.0.0.0", port: int = 8000):
    """启动API服务器
    
    Args:
        config_path: 配置文件路径
        host: 监听地址
        port: 监听端口
    """
    print(f"启动API服务器: http://{host}:{port}")
    
    # 创建API服务器
    api = create_web_api(config_path)
    
    try:
        # 启动服务器
        await api.start_server(host, port)
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭API服务器...")


async def start_web_server(config_path: str, host: str = "0.0.0.0", port: int = 8000):
    """启动Web服务器
    
    Args:
        config_path: 配置文件路径
        host: 监听地址
        port: 监听端口
    """
    print(f"启动Web服务器: http://{host}:{port}")
    print(f"Web界面: http://{host}:{port}/web")
    print(f"仪表板: http://{host}:{port}/dashboard")
    print(f"API文档: http://{host}:{port}/docs")
    
    # 创建Web服务器
    server = create_static_server(config_path)
    
    try:
        # 启动服务器
        await server.start_server(host, port)
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭Web服务器...")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="量化交易系统启动脚本")
    parser.add_argument("mode", choices=["service", "api", "web"], 
                       help="启动模式")
    parser.add_argument("--config", "-c", default="config/config.yaml", 
                       help="配置文件路径")
    parser.add_argument("--host", default="0.0.0.0", 
                       help="监听地址")
    parser.add_argument("--port", type=int, default=8000, 
                       help="监听端口")
    
    args = parser.parse_args()
    
    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return 1
    
    try:
        if args.mode == "service":
            # 启动交易服务
            success = asyncio.run(start_trading_service(str(config_path)))
            return 0 if success else 1
        elif args.mode == "api":
            # 启动API服务器
            asyncio.run(start_api_server(str(config_path), args.host, args.port))
            return 0
        elif args.mode == "web":
            # 启动Web服务器
            asyncio.run(start_web_server(str(config_path), args.host, args.port))
            return 0
        else:
            print(f"❌ 未知启动模式: {args.mode}")
            return 1
            
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
