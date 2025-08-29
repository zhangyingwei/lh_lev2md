"""
Web前端界面测试脚本

测试Web前端界面的各项功能，包括页面加载、API集成和用户交互
"""

import asyncio
import aiohttp
from pathlib import Path

from .static_server import create_static_server
from ..utils.logger import setup_logger


class WebInterfaceTester:
    """Web前端界面测试类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化测试器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.logger = setup_logger({})
        
        # 创建静态服务器
        self.server = create_static_server(config_path)
        
        # 测试结果收集
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0
        }
        
        self.logger.info("Web前端界面测试器初始化完成")
    
    async def test_server_creation(self) -> bool:
        """测试服务器创建
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试服务器创建...")
        self.test_results['total_tests'] += 1
        
        try:
            # 检查服务器实例
            if not self.server:
                self.logger.error("服务器实例创建失败")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查FastAPI应用
            app = self.server.app
            if not app:
                self.logger.error("FastAPI应用未创建")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查路由注册
            routes = [route.path for route in app.routes]
            expected_routes = ['/web', '/dashboard', '/static']
            
            for expected_route in expected_routes:
                if not any(expected_route in route for route in routes):
                    self.logger.error(f"缺少路由: {expected_route}")
                    self.test_results['failed_tests'] += 1
                    return False
            
            self.logger.info("✅ 服务器创建测试通过")
            self.test_results['passed_tests'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"服务器创建测试失败: {e}")
            self.test_results['failed_tests'] += 1
            return False
    
    async def test_html_generation(self) -> bool:
        """测试HTML页面生成
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试HTML页面生成...")
        self.test_results['total_tests'] += 1
        
        try:
            # 测试默认HTML生成
            default_html = self.server._get_default_html()
            if not default_html or len(default_html) < 100:
                self.logger.error("默认HTML生成失败")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查HTML内容
            required_elements = [
                '<title>量化交易系统</title>',
                'startSystem()',
                'stopSystem()',
                'checkStatus()'
            ]
            
            for element in required_elements:
                if element not in default_html:
                    self.logger.error(f"默认HTML缺少元素: {element}")
                    self.test_results['failed_tests'] += 1
                    return False
            
            # 测试仪表板HTML生成
            dashboard_html = self.server._get_dashboard_html()
            if not dashboard_html or len(dashboard_html) < 100:
                self.logger.error("仪表板HTML生成失败")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查仪表板内容
            dashboard_elements = [
                '<title>量化交易系统 - 仪表板</title>',
                'loadEvents()',
                'loadRecommendations()',
                'subscribeStocks()'
            ]
            
            for element in dashboard_elements:
                if element not in dashboard_html:
                    self.logger.error(f"仪表板HTML缺少元素: {element}")
                    self.test_results['failed_tests'] += 1
                    return False
            
            self.logger.info("✅ HTML页面生成测试通过")
            self.test_results['passed_tests'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"HTML页面生成测试失败: {e}")
            self.test_results['failed_tests'] += 1
            return False
    
    async def test_static_directories(self) -> bool:
        """测试静态文件目录
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试静态文件目录...")
        self.test_results['total_tests'] += 1
        
        try:
            # 检查静态文件目录
            if not self.server.static_dir.exists():
                self.logger.error("静态文件目录不存在")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查模板目录
            if not self.server.templates_dir.exists():
                self.logger.error("模板目录不存在")
                self.test_results['failed_tests'] += 1
                return False
            
            self.logger.info(f"静态文件目录: {self.server.static_dir}")
            self.logger.info(f"模板目录: {self.server.templates_dir}")
            
            self.logger.info("✅ 静态文件目录测试通过")
            self.test_results['passed_tests'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"静态文件目录测试失败: {e}")
            self.test_results['failed_tests'] += 1
            return False
    
    async def test_api_integration(self) -> bool:
        """测试API集成
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试API集成...")
        self.test_results['total_tests'] += 1
        
        try:
            # 检查API实例
            api = self.server.api
            if not api:
                self.logger.error("API实例未创建")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查API路由
            app = api.app
            api_routes = [route.path for route in app.routes]
            
            expected_api_routes = [
                '/',
                '/health',
                '/system/start',
                '/system/stop',
                '/system/status',
                '/events',
                '/recommendations'
            ]
            
            for expected_route in expected_api_routes:
                if expected_route not in api_routes:
                    self.logger.error(f"缺少API路由: {expected_route}")
                    self.test_results['failed_tests'] += 1
                    return False
            
            self.logger.info("✅ API集成测试通过")
            self.test_results['passed_tests'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"API集成测试失败: {e}")
            self.test_results['failed_tests'] += 1
            return False
    
    async def test_route_functionality(self) -> bool:
        """测试路由功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试路由功能...")
        self.test_results['total_tests'] += 1
        
        try:
            from fastapi.testclient import TestClient
            
            # 创建测试客户端
            client = TestClient(self.server.app)
            
            # 测试Web界面路由
            web_response = client.get("/web")
            if web_response.status_code != 200:
                self.logger.error(f"Web界面路由失败: {web_response.status_code}")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查响应内容
            if "量化交易系统" not in web_response.text:
                self.logger.error("Web界面内容不正确")
                self.test_results['failed_tests'] += 1
                return False
            
            # 测试仪表板路由
            dashboard_response = client.get("/dashboard")
            if dashboard_response.status_code != 200:
                self.logger.error(f"仪表板路由失败: {dashboard_response.status_code}")
                self.test_results['failed_tests'] += 1
                return False
            
            # 检查仪表板内容
            if "仪表板" not in dashboard_response.text:
                self.logger.error("仪表板内容不正确")
                self.test_results['failed_tests'] += 1
                return False
            
            self.logger.info("✅ 路由功能测试通过")
            self.test_results['passed_tests'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"路由功能测试失败: {e}")
            self.test_results['failed_tests'] += 1
            return False
    
    async def test_javascript_functionality(self) -> bool:
        """测试JavaScript功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试JavaScript功能...")
        self.test_results['total_tests'] += 1
        
        try:
            # 检查默认HTML中的JavaScript函数
            default_html = self.server._get_default_html()
            
            js_functions = [
                'async function apiCall',
                'async function startSystem',
                'async function stopSystem',
                'async function checkStatus'
            ]
            
            for func in js_functions:
                if func not in default_html:
                    self.logger.error(f"默认HTML缺少JavaScript函数: {func}")
                    self.test_results['failed_tests'] += 1
                    return False
            
            # 检查仪表板HTML中的JavaScript函数
            dashboard_html = self.server._get_dashboard_html()
            
            dashboard_js_functions = [
                'async function loadSystemStatus',
                'async function loadEvents',
                'async function loadRecommendations',
                'async function subscribeStocks'
            ]
            
            for func in dashboard_js_functions:
                if func not in dashboard_html:
                    self.logger.error(f"仪表板HTML缺少JavaScript函数: {func}")
                    self.test_results['failed_tests'] += 1
                    return False
            
            self.logger.info("✅ JavaScript功能测试通过")
            self.test_results['passed_tests'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"JavaScript功能测试失败: {e}")
            self.test_results['failed_tests'] += 1
            return False
    
    async def run_all_tests(self) -> bool:
        """运行所有测试
        
        Returns:
            bool: 所有测试是否通过
        """
        self.logger.info("开始Web前端界面完整测试")
        
        tests = [
            ("服务器创建测试", self.test_server_creation),
            ("HTML页面生成测试", self.test_html_generation),
            ("静态文件目录测试", self.test_static_directories),
            ("API集成测试", self.test_api_integration),
            ("路由功能测试", self.test_route_functionality),
            ("JavaScript功能测试", self.test_javascript_functionality)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            self.logger.info(f"执行 {test_name}...")
            try:
                result = await test_func()
                results.append(result)
                if result:
                    self.logger.info(f"✅ {test_name} 通过")
                else:
                    self.logger.error(f"❌ {test_name} 失败")
            except Exception as e:
                self.logger.error(f"❌ {test_name} 异常: {e}")
                results.append(False)
        
        success_count = self.test_results['passed_tests']
        total_count = self.test_results['total_tests']
        
        self.logger.info(f"测试完成: {success_count}/{total_count} 通过")
        
        return all(results)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web前端界面测试")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--test", "-t", 
                       choices=["server", "html", "static", "api", "routes", "js", "all"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = WebInterfaceTester(args.config)
    
    try:
        if args.test == "server":
            success = await tester.test_server_creation()
        elif args.test == "html":
            success = await tester.test_html_generation()
        elif args.test == "static":
            success = await tester.test_static_directories()
        elif args.test == "api":
            success = await tester.test_api_integration()
        elif args.test == "routes":
            success = await tester.test_route_functionality()
        elif args.test == "js":
            success = await tester.test_javascript_functionality()
        else:
            success = await tester.run_all_tests()
        
        if success:
            print("✅ 所有测试通过")
            return 0
        else:
            print("❌ 部分测试失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"测试异常: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
