"""
Web API接口测试脚本

测试RESTful API接口的各项功能，包括数据查询、推荐获取和系统监控
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any

from ..utils.logger import setup_logger


class WebAPITester:
    """Web API测试类"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化测试器
        
        Args:
            base_url: API服务器基础URL
        """
        self.base_url = base_url
        self.logger = setup_logger({})
        
        # 测试结果收集
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
        
        self.logger.info("Web API测试器初始化完成")
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            响应数据
        """
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {"status_code": response.status, "text": await response.text()}
    
    async def _test_endpoint(self, name: str, method: str, endpoint: str, 
                           expected_status: int = 200, **kwargs) -> bool:
        """测试单个API端点
        
        Args:
            name: 测试名称
            method: HTTP方法
            endpoint: API端点
            expected_status: 期望状态码
            **kwargs: 请求参数
            
        Returns:
            bool: 测试是否通过
        """
        self.test_results['total_tests'] += 1
        
        try:
            self.logger.info(f"测试 {name}: {method} {endpoint}")
            
            response = await self._make_request(method, endpoint, **kwargs)
            
            # 检查状态码
            status_code = response.get('status_code', 200)
            if status_code != expected_status:
                self.logger.error(f"状态码错误: 期望 {expected_status}, 实际 {status_code}")
                self._record_test_result(name, False, f"状态码错误: {status_code}")
                return False
            
            # 检查响应格式
            if 'success' in response:
                if not response['success']:
                    self.logger.warning(f"API返回失败: {response.get('message', '未知错误')}")
                    self._record_test_result(name, False, response.get('message', '未知错误'))
                    return False
            
            self.logger.info(f"✅ {name} 测试通过")
            self._record_test_result(name, True, "测试通过")
            self.test_results['passed_tests'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"❌ {name} 测试失败: {e}")
            self._record_test_result(name, False, str(e))
            self.test_results['failed_tests'] += 1
            return False
    
    def _record_test_result(self, name: str, passed: bool, message: str):
        """记录测试结果
        
        Args:
            name: 测试名称
            passed: 是否通过
            message: 结果消息
        """
        self.test_results['test_details'].append({
            'name': name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    async def test_basic_endpoints(self) -> bool:
        """测试基础端点
        
        Returns:
            bool: 测试是否通过
        """
        self.logger.info("开始测试基础端点...")
        
        tests = [
            ("根路径", "GET", "/"),
            ("健康检查", "GET", "/health", 503),  # 系统未启动时应该返回503
            ("获取预设条件", "GET", "/presets", 503),  # 系统未启动时应该返回503
        ]
        
        results = []
        for name, method, endpoint, *args in tests:
            expected_status = args[0] if args else 200
            result = await self._test_endpoint(name, method, endpoint, expected_status)
            results.append(result)
        
        return all(results)
    
    async def test_system_management(self) -> bool:
        """测试系统管理端点
        
        Returns:
            bool: 测试是否通过
        """
        self.logger.info("开始测试系统管理端点...")
        
        # 启动系统
        start_result = await self._test_endpoint("启动系统", "POST", "/system/start")
        if not start_result:
            return False
        
        # 等待系统启动
        await asyncio.sleep(3)
        
        # 获取系统状态
        status_result = await self._test_endpoint("获取系统状态", "GET", "/system/status")
        
        # 获取系统统计
        stats_result = await self._test_endpoint("获取系统统计", "GET", "/system/statistics")
        
        # 健康检查（系统启动后应该正常）
        health_result = await self._test_endpoint("健康检查（系统运行中）", "GET", "/health")
        
        # 停止系统
        stop_result = await self._test_endpoint("停止系统", "POST", "/system/stop")
        
        return all([start_result, status_result, stats_result, health_result, stop_result])
    
    async def test_data_endpoints(self) -> bool:
        """测试数据端点
        
        Returns:
            bool: 测试是否通过
        """
        self.logger.info("开始测试数据端点...")
        
        # 先启动系统
        await self._test_endpoint("启动系统", "POST", "/system/start")
        await asyncio.sleep(2)
        
        # 订阅股票数据
        subscribe_data = {"stock_codes": ["000001", "600000", "600519"]}
        subscribe_result = await self._test_endpoint(
            "订阅股票数据", "POST", "/data/subscribe",
            json=subscribe_data,
            headers={"Content-Type": "application/json"}
        )
        
        # 等待数据处理
        await asyncio.sleep(3)
        
        # 获取炸板事件
        events_result = await self._test_endpoint("获取炸板事件", "GET", "/events?limit=10")
        
        # 获取股票推荐
        recommendations_result = await self._test_endpoint("获取股票推荐", "GET", "/recommendations?limit=5")
        
        # 获取预设条件
        presets_result = await self._test_endpoint("获取预设条件", "GET", "/presets")
        
        # 停止系统
        await self._test_endpoint("停止系统", "POST", "/system/stop")
        
        return all([subscribe_result, events_result, recommendations_result, presets_result])
    
    async def test_query_parameters(self) -> bool:
        """测试查询参数
        
        Returns:
            bool: 测试是否通过
        """
        self.logger.info("开始测试查询参数...")
        
        # 启动系统
        await self._test_endpoint("启动系统", "POST", "/system/start")
        await asyncio.sleep(2)
        
        # 测试事件查询参数
        events_tests = [
            ("获取事件（限制数量）", "GET", "/events?limit=5"),
            ("获取事件（时间筛选）", "GET", "/events?hours=1"),
            ("获取事件（股票筛选）", "GET", "/events?stock_code=000001"),
            ("获取事件（组合参数）", "GET", "/events?limit=3&hours=6&stock_code=000001")
        ]
        
        events_results = []
        for name, method, endpoint in events_tests:
            result = await self._test_endpoint(name, method, endpoint)
            events_results.append(result)
        
        # 测试推荐查询参数
        recommendations_tests = [
            ("获取推荐（限制数量）", "GET", "/recommendations?limit=3"),
            ("获取推荐（最低评分）", "GET", "/recommendations?min_score=50"),
            ("获取推荐（筛选预设）", "GET", "/recommendations?filter_preset=high_quality"),
            ("获取推荐（排序预设）", "GET", "/recommendations?sort_preset=by_score")
        ]
        
        recommendations_results = []
        for name, method, endpoint in recommendations_tests:
            result = await self._test_endpoint(name, method, endpoint)
            recommendations_results.append(result)
        
        # 停止系统
        await self._test_endpoint("停止系统", "POST", "/system/stop")
        
        return all(events_results + recommendations_results)
    
    async def test_error_handling(self) -> bool:
        """测试错误处理
        
        Returns:
            bool: 测试是否通过
        """
        self.logger.info("开始测试错误处理...")
        
        # 测试无效端点
        invalid_result = await self._test_endpoint(
            "无效端点", "GET", "/invalid/endpoint", 404
        )
        
        # 测试无效参数
        invalid_params_result = await self._test_endpoint(
            "无效参数", "GET", "/events?limit=invalid", 422
        )
        
        # 测试系统未启动时的操作
        not_started_result = await self._test_endpoint(
            "系统未启动时获取状态", "GET", "/system/status", 503
        )
        
        return all([invalid_result, invalid_params_result, not_started_result])
    
    async def run_all_tests(self) -> bool:
        """运行所有测试
        
        Returns:
            bool: 所有测试是否通过
        """
        self.logger.info("开始Web API完整测试")
        
        tests = [
            ("基础端点测试", self.test_basic_endpoints),
            ("系统管理测试", self.test_system_management),
            ("数据端点测试", self.test_data_endpoints),
            ("查询参数测试", self.test_query_parameters),
            ("错误处理测试", self.test_error_handling)
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
            
            # 测试间隔
            await asyncio.sleep(1)
        
        # 输出测试总结
        self.logger.info(f"测试完成: {self.test_results['passed_tests']}/{self.test_results['total_tests']} 通过")
        
        return all(results)
    
    def get_test_report(self) -> Dict[str, Any]:
        """获取测试报告
        
        Returns:
            测试报告字典
        """
        return {
            'summary': {
                'total_tests': self.test_results['total_tests'],
                'passed_tests': self.test_results['passed_tests'],
                'failed_tests': self.test_results['failed_tests'],
                'success_rate': self.test_results['passed_tests'] / max(self.test_results['total_tests'], 1)
            },
            'details': self.test_results['test_details']
        }


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web API接口测试")
    parser.add_argument("--url", default="http://localhost:8000", help="API服务器URL")
    parser.add_argument("--test", "-t", 
                       choices=["basic", "system", "data", "params", "errors", "all"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = WebAPITester(args.url)
    
    try:
        if args.test == "basic":
            success = await tester.test_basic_endpoints()
        elif args.test == "system":
            success = await tester.test_system_management()
        elif args.test == "data":
            success = await tester.test_data_endpoints()
        elif args.test == "params":
            success = await tester.test_query_parameters()
        elif args.test == "errors":
            success = await tester.test_error_handling()
        else:
            success = await tester.run_all_tests()
        
        # 输出测试报告
        report = tester.get_test_report()
        print(f"\n测试报告:")
        print(f"总测试数: {report['summary']['total_tests']}")
        print(f"通过测试: {report['summary']['passed_tests']}")
        print(f"失败测试: {report['summary']['failed_tests']}")
        print(f"成功率: {report['summary']['success_rate']:.2%}")
        
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
