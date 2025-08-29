#!/usr/bin/env python3
"""
量化交易系统部署脚本

提供完整的系统部署、启动、停止和监控功能
"""

import os
import sys
import subprocess
import argparse
import time
import signal
import psutil
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import json


class TradingSystemDeployer:
    """量化交易系统部署器"""
    
    def __init__(self, project_root: str = None):
        """初始化部署器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root or os.getcwd())
        self.config_file = self.project_root / "config" / "config.yaml"
        self.pid_file = self.project_root / "logs" / "trading_system.pid"
        self.log_dir = self.project_root / "logs"
        
        # 确保目录存在
        self.log_dir.mkdir(exist_ok=True)
        
        print(f"项目根目录: {self.project_root}")
    
    def check_environment(self) -> bool:
        """检查部署环境
        
        Returns:
            bool: 环境检查是否通过
        """
        print("检查部署环境...")
        
        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 8):
            print(f"❌ Python版本过低: {python_version}, 需要3.8+")
            return False
        print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 检查uv是否安装
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ uv版本: {result.stdout.strip()}")
            else:
                print("❌ uv未安装或不可用")
                return False
        except FileNotFoundError:
            print("❌ uv未安装")
            return False
        
        # 检查配置文件
        if not self.config_file.exists():
            print(f"❌ 配置文件不存在: {self.config_file}")
            return False
        print(f"✅ 配置文件: {self.config_file}")
        
        # 检查项目结构
        required_dirs = ["src", "config", "data", "logs"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                print(f"❌ 缺少目录: {dir_path}")
                return False
            print(f"✅ 目录存在: {dir_name}")
        
        print("✅ 环境检查通过")
        return True
    
    def install_dependencies(self) -> bool:
        """安装依赖
        
        Returns:
            bool: 安装是否成功
        """
        print("安装项目依赖...")
        
        try:
            # 使用uv安装依赖
            result = subprocess.run(
                ["uv", "sync"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ 依赖安装成功")
                return True
            else:
                print(f"❌ 依赖安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 依赖安装异常: {e}")
            return False
    
    def setup_database(self) -> bool:
        """设置数据库
        
        Returns:
            bool: 设置是否成功
        """
        print("设置数据库...")
        
        try:
            # 运行数据库初始化脚本
            result = subprocess.run(
                ["uv", "run", "python", "-c", 
                 "from src.trading_system.models.database_init import initialize_database; "
                 "initialize_database('sqlite:///data/trading_system.db'); "
                 "print('数据库初始化完成')"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ 数据库设置成功")
                print(result.stdout)
                return True
            else:
                print(f"❌ 数据库设置失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 数据库设置异常: {e}")
            return False
    
    def start_system(self, mode: str = "api") -> bool:
        """启动系统
        
        Args:
            mode: 启动模式 (api, service, web)
            
        Returns:
            bool: 启动是否成功
        """
        print(f"启动系统 (模式: {mode})...")
        
        # 检查是否已经运行
        if self.is_running():
            print("❌ 系统已在运行中")
            return False
        
        try:
            if mode == "api":
                # 启动API服务器
                cmd = ["uv", "run", "python", "-m", "src.trading_system.api.server", 
                       "--config", str(self.config_file)]
            elif mode == "service":
                # 启动交易服务
                cmd = ["uv", "run", "python", "-m", "src.trading_system.main", 
                       "--config", str(self.config_file)]
            elif mode == "web":
                # 启动Web服务器
                cmd = ["uv", "run", "python", "-c",
                       f"import asyncio; "
                       f"from src.trading_system.web.static_server import create_static_server; "
                       f"server = create_static_server('{self.config_file}'); "
                       f"asyncio.run(server.start_server())"]
            else:
                print(f"❌ 未知启动模式: {mode}")
                return False
            
            # 启动进程
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # 保存PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # 等待启动
            time.sleep(3)
            
            if process.poll() is None:
                print(f"✅ 系统启动成功 (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ 系统启动失败: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ 系统启动异常: {e}")
            return False
    
    def stop_system(self) -> bool:
        """停止系统
        
        Returns:
            bool: 停止是否成功
        """
        print("停止系统...")
        
        if not self.is_running():
            print("✅ 系统未运行")
            return True
        
        try:
            # 读取PID
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # 终止进程
            if os.name == 'nt':
                # Windows
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
            else:
                # Unix/Linux
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            
            # 等待进程结束
            time.sleep(2)
            
            # 删除PID文件
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("✅ 系统停止成功")
            return True
            
        except Exception as e:
            print(f"❌ 系统停止异常: {e}")
            return False
    
    def restart_system(self, mode: str = "api") -> bool:
        """重启系统
        
        Args:
            mode: 启动模式
            
        Returns:
            bool: 重启是否成功
        """
        print("重启系统...")
        
        # 停止系统
        self.stop_system()
        
        # 等待
        time.sleep(2)
        
        # 启动系统
        return self.start_system(mode)
    
    def is_running(self) -> bool:
        """检查系统是否运行
        
        Returns:
            bool: 系统是否运行
        """
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            return psutil.pid_exists(pid)
            
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态
        
        Returns:
            Dict: 系统状态信息
        """
        status = {
            "running": self.is_running(),
            "pid": None,
            "memory_usage": None,
            "cpu_usage": None,
            "uptime": None
        }
        
        if status["running"] and self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                process = psutil.Process(pid)
                status["pid"] = pid
                status["memory_usage"] = process.memory_info().rss / 1024 / 1024  # MB
                status["cpu_usage"] = process.cpu_percent()
                status["uptime"] = time.time() - process.create_time()
                
            except Exception as e:
                print(f"获取状态信息失败: {e}")
        
        return status
    
    def run_tests(self) -> bool:
        """运行测试
        
        Returns:
            bool: 测试是否通过
        """
        print("运行系统测试...")
        
        test_modules = [
            "src.trading_system.models.test_models",
            "src.trading_system.data.test_level2_service",
            "src.trading_system.algorithms.test_limit_up_analyzer",
            "src.trading_system.algorithms.test_stock_filter",
            "src.trading_system.algorithms.test_realtime_engine",
            "src.trading_system.services.test_trading_service",
            "src.trading_system.web.test_web_interface"
        ]
        
        all_passed = True
        
        for module in test_modules:
            print(f"测试模块: {module}")
            try:
                result = subprocess.run(
                    ["uv", "run", "python", "-m", module, "--test", "all"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    print(f"✅ {module} 测试通过")
                else:
                    print(f"❌ {module} 测试失败")
                    print(result.stderr)
                    all_passed = False
                    
            except subprocess.TimeoutExpired:
                print(f"❌ {module} 测试超时")
                all_passed = False
            except Exception as e:
                print(f"❌ {module} 测试异常: {e}")
                all_passed = False
        
        if all_passed:
            print("✅ 所有测试通过")
        else:
            print("❌ 部分测试失败")
        
        return all_passed
    
    def deploy(self, mode: str = "api", skip_tests: bool = False) -> bool:
        """完整部署流程
        
        Args:
            mode: 启动模式
            skip_tests: 是否跳过测试
            
        Returns:
            bool: 部署是否成功
        """
        print("开始完整部署流程...")
        
        # 1. 环境检查
        if not self.check_environment():
            return False
        
        # 2. 安装依赖
        if not self.install_dependencies():
            return False
        
        # 3. 设置数据库
        if not self.setup_database():
            return False
        
        # 4. 运行测试
        if not skip_tests and not self.run_tests():
            print("⚠️ 测试失败，但继续部署")
        
        # 5. 启动系统
        if not self.start_system(mode):
            return False
        
        print("✅ 部署完成")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="量化交易系统部署工具")
    parser.add_argument("action", choices=["deploy", "start", "stop", "restart", "status", "test"],
                       help="执行的操作")
    parser.add_argument("--mode", choices=["api", "service", "web"], default="api",
                       help="启动模式")
    parser.add_argument("--project-root", help="项目根目录")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试")
    
    args = parser.parse_args()
    
    # 创建部署器
    deployer = TradingSystemDeployer(args.project_root)
    
    try:
        if args.action == "deploy":
            success = deployer.deploy(args.mode, args.skip_tests)
        elif args.action == "start":
            success = deployer.start_system(args.mode)
        elif args.action == "stop":
            success = deployer.stop_system()
        elif args.action == "restart":
            success = deployer.restart_system(args.mode)
        elif args.action == "status":
            status = deployer.get_status()
            print(f"系统状态: {json.dumps(status, indent=2)}")
            success = True
        elif args.action == "test":
            success = deployer.run_tests()
        else:
            print(f"未知操作: {args.action}")
            success = False
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return 1
    except Exception as e:
        print(f"操作异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
