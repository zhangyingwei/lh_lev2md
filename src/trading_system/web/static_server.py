"""
静态文件服务器

提供Web前端静态文件服务，集成API接口
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from ..api.web_api import TradingSystemAPI


class StaticFileServer:
    """静态文件服务器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化静态文件服务器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        
        # 创建API实例
        self.api = TradingSystemAPI(config_path)
        self.app = self.api.app
        
        # 静态文件目录
        self.static_dir = Path(__file__).parent / "static"
        self.templates_dir = Path(__file__).parent / "templates"
        
        # 确保目录存在
        self.static_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        
        # 注册静态文件路由
        self._register_static_routes()
    
    def _register_static_routes(self):
        """注册静态文件路由"""
        
        # 挂载静态文件目录
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")
        
        @self.app.get("/web", response_class=HTMLResponse)
        async def web_interface():
            """Web界面主页"""
            html_file = self.templates_dir / "index.html"
            if html_file.exists():
                return HTMLResponse(content=html_file.read_text(encoding='utf-8'))
            else:
                return HTMLResponse(content=self._get_default_html())
        
        @self.app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            """仪表板页面"""
            html_file = self.templates_dir / "dashboard.html"
            if html_file.exists():
                return HTMLResponse(content=html_file.read_text(encoding='utf-8'))
            else:
                return HTMLResponse(content=self._get_dashboard_html())
    
    def _get_default_html(self) -> str:
        """获取默认HTML页面"""
        return """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>量化交易系统</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { text-align: center; margin-bottom: 30px; }
                .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
                .btn:hover { background: #0056b3; }
                .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
                .status.running { background: #d4edda; color: #155724; }
                .status.stopped { background: #f8d7da; color: #721c24; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>量化交易系统</h1>
                    <p>基于Level2行情数据的涨停炸板分析系统</p>
                </div>
                
                <div class="card">
                    <h2>系统控制</h2>
                    <div id="systemStatus" class="status stopped">系统状态: 未知</div>
                    <button class="btn" onclick="startSystem()">启动系统</button>
                    <button class="btn" onclick="stopSystem()">停止系统</button>
                    <button class="btn" onclick="checkStatus()">检查状态</button>
                </div>
                
                <div class="card">
                    <h2>快速导航</h2>
                    <a href="/dashboard" class="btn">仪表板</a>
                    <a href="/docs" class="btn">API文档</a>
                    <a href="/redoc" class="btn">API参考</a>
                </div>
            </div>
            
            <script>
                async function apiCall(method, endpoint, data = null) {
                    const options = { method };
                    if (data) {
                        options.headers = { 'Content-Type': 'application/json' };
                        options.body = JSON.stringify(data);
                    }
                    const response = await fetch(endpoint, options);
                    return await response.json();
                }
                
                async function startSystem() {
                    try {
                        const result = await apiCall('POST', '/system/start');
                        alert(result.message);
                        checkStatus();
                    } catch (error) {
                        alert('启动失败: ' + error.message);
                    }
                }
                
                async function stopSystem() {
                    try {
                        const result = await apiCall('POST', '/system/stop');
                        alert(result.message);
                        checkStatus();
                    } catch (error) {
                        alert('停止失败: ' + error.message);
                    }
                }
                
                async function checkStatus() {
                    try {
                        const result = await apiCall('GET', '/system/status');
                        const statusDiv = document.getElementById('systemStatus');
                        if (result.data.is_running) {
                            statusDiv.className = 'status running';
                            statusDiv.textContent = '系统状态: 运行中';
                        } else {
                            statusDiv.className = 'status stopped';
                            statusDiv.textContent = '系统状态: 已停止';
                        }
                    } catch (error) {
                        const statusDiv = document.getElementById('systemStatus');
                        statusDiv.className = 'status stopped';
                        statusDiv.textContent = '系统状态: 连接失败';
                    }
                }
                
                // 页面加载时检查状态
                window.onload = checkStatus;
            </script>
        </body>
        </html>
        """
    
    def _get_dashboard_html(self) -> str:
        """获取仪表板HTML页面"""
        return """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>量化交易系统 - 仪表板</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 1400px; margin: 0 auto; }
                .header { text-align: center; margin-bottom: 30px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .card h3 { margin-top: 0; color: #333; }
                .btn { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 5px; }
                .btn:hover { background: #0056b3; }
                .btn.success { background: #28a745; }
                .btn.danger { background: #dc3545; }
                .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
                .status-running { background: #28a745; }
                .status-stopped { background: #dc3545; }
                .table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                .table th, .table td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                .table th { background-color: #f8f9fa; }
                .metric { text-align: center; margin: 10px 0; }
                .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
                .metric-label { color: #666; }
                .refresh-btn { float: right; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>量化交易系统仪表板</h1>
                    <button class="btn refresh-btn" onclick="refreshAll()">刷新数据</button>
                </div>
                
                <div class="grid">
                    <!-- 系统状态卡片 -->
                    <div class="card">
                        <h3>系统状态</h3>
                        <div id="systemStatus">
                            <span class="status-indicator status-stopped"></span>
                            <span>检查中...</span>
                        </div>
                        <div class="metric">
                            <div class="metric-value" id="uptime">--</div>
                            <div class="metric-label">运行时间(秒)</div>
                        </div>
                        <button class="btn success" onclick="startSystem()">启动</button>
                        <button class="btn danger" onclick="stopSystem()">停止</button>
                    </div>
                    
                    <!-- 数据统计卡片 -->
                    <div class="card">
                        <h3>数据统计</h3>
                        <div class="metric">
                            <div class="metric-value" id="totalEvents">--</div>
                            <div class="metric-label">炸板事件总数</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value" id="totalRecommendations">--</div>
                            <div class="metric-label">推荐总数</div>
                        </div>
                    </div>
                    
                    <!-- 股票订阅卡片 -->
                    <div class="card">
                        <h3>股票订阅</h3>
                        <input type="text" id="stockInput" placeholder="输入股票代码，用逗号分隔" style="width: 100%; padding: 8px; margin-bottom: 10px;">
                        <button class="btn" onclick="subscribeStocks()">订阅股票</button>
                        <div id="subscriptionStatus" style="margin-top: 10px;"></div>
                    </div>
                </div>
                
                <div class="grid" style="margin-top: 20px;">
                    <!-- 最新炸板事件 -->
                    <div class="card" style="grid-column: 1 / -1;">
                        <h3>最新炸板事件 <button class="btn" onclick="loadEvents()">刷新</button></h3>
                        <table class="table" id="eventsTable">
                            <thead>
                                <tr>
                                    <th>股票代码</th>
                                    <th>炸板时间</th>
                                    <th>涨停价</th>
                                    <th>炸板价</th>
                                    <th>成交量</th>
                                    <th>评分</th>
                                </tr>
                            </thead>
                            <tbody id="eventsBody">
                                <tr><td colspan="6">暂无数据</td></tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- 股票推荐 -->
                    <div class="card" style="grid-column: 1 / -1;">
                        <h3>股票推荐 <button class="btn" onclick="loadRecommendations()">刷新</button></h3>
                        <table class="table" id="recommendationsTable">
                            <thead>
                                <tr>
                                    <th>排名</th>
                                    <th>股票代码</th>
                                    <th>当前价格</th>
                                    <th>综合评分</th>
                                    <th>风险等级</th>
                                    <th>置信度</th>
                                    <th>推荐理由</th>
                                </tr>
                            </thead>
                            <tbody id="recommendationsBody">
                                <tr><td colspan="7">暂无数据</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <script>
                async function apiCall(method, endpoint, data = null) {
                    const options = { method };
                    if (data) {
                        options.headers = { 'Content-Type': 'application/json' };
                        options.body = JSON.stringify(data);
                    }
                    const response = await fetch(endpoint, options);
                    return await response.json();
                }
                
                async function loadSystemStatus() {
                    try {
                        const result = await apiCall('GET', '/system/status');
                        const statusDiv = document.getElementById('systemStatus');
                        const uptimeDiv = document.getElementById('uptime');
                        
                        if (result.data.is_running) {
                            statusDiv.innerHTML = '<span class="status-indicator status-running"></span><span>系统运行中</span>';
                            uptimeDiv.textContent = result.data.uptime_seconds || 0;
                        } else {
                            statusDiv.innerHTML = '<span class="status-indicator status-stopped"></span><span>系统已停止</span>';
                            uptimeDiv.textContent = 0;
                        }
                        
                        document.getElementById('totalEvents').textContent = result.data.total_events_detected || 0;
                        document.getElementById('totalRecommendations').textContent = result.data.total_recommendations || 0;
                    } catch (error) {
                        document.getElementById('systemStatus').innerHTML = '<span class="status-indicator status-stopped"></span><span>连接失败</span>';
                    }
                }
                
                async function loadEvents() {
                    try {
                        const result = await apiCall('GET', '/events?limit=10');
                        const tbody = document.getElementById('eventsBody');
                        
                        if (result.data.events && result.data.events.length > 0) {
                            tbody.innerHTML = result.data.events.map(event => `
                                <tr>
                                    <td>${event.stock_code}</td>
                                    <td>${new Date(event.break_time).toLocaleString()}</td>
                                    <td>${event.limit_up_price.toFixed(2)}</td>
                                    <td>${event.break_price.toFixed(2)}</td>
                                    <td>${event.break_volume.toLocaleString()}</td>
                                    <td>${event.score.toFixed(2)}</td>
                                </tr>
                            `).join('');
                        } else {
                            tbody.innerHTML = '<tr><td colspan="6">暂无数据</td></tr>';
                        }
                    } catch (error) {
                        console.error('加载事件失败:', error);
                    }
                }
                
                async function loadRecommendations() {
                    try {
                        const result = await apiCall('GET', '/recommendations?limit=10');
                        const tbody = document.getElementById('recommendationsBody');
                        
                        if (result.data.recommendations && result.data.recommendations.length > 0) {
                            tbody.innerHTML = result.data.recommendations.map(rec => `
                                <tr>
                                    <td>${rec.rank}</td>
                                    <td>${rec.stock_code}</td>
                                    <td>${rec.current_price.toFixed(2)}</td>
                                    <td>${rec.total_score.toFixed(2)}</td>
                                    <td>${rec.risk_level}</td>
                                    <td>${(rec.confidence * 100).toFixed(1)}%</td>
                                    <td>${rec.recommendation_reason}</td>
                                </tr>
                            `).join('');
                        } else {
                            tbody.innerHTML = '<tr><td colspan="7">暂无数据</td></tr>';
                        }
                    } catch (error) {
                        console.error('加载推荐失败:', error);
                    }
                }
                
                async function startSystem() {
                    try {
                        const result = await apiCall('POST', '/system/start');
                        alert(result.message);
                        setTimeout(loadSystemStatus, 2000);
                    } catch (error) {
                        alert('启动失败: ' + error.message);
                    }
                }
                
                async function stopSystem() {
                    try {
                        const result = await apiCall('POST', '/system/stop');
                        alert(result.message);
                        setTimeout(loadSystemStatus, 1000);
                    } catch (error) {
                        alert('停止失败: ' + error.message);
                    }
                }
                
                async function subscribeStocks() {
                    const input = document.getElementById('stockInput');
                    const stockCodes = input.value.split(',').map(s => s.trim()).filter(s => s);
                    
                    if (stockCodes.length === 0) {
                        alert('请输入股票代码');
                        return;
                    }
                    
                    try {
                        const result = await apiCall('POST', '/data/subscribe', stockCodes);
                        document.getElementById('subscriptionStatus').innerHTML = 
                            `<span style="color: green;">订阅成功: ${stockCodes.join(', ')}</span>`;
                        input.value = '';
                    } catch (error) {
                        document.getElementById('subscriptionStatus').innerHTML = 
                            `<span style="color: red;">订阅失败: ${error.message}</span>`;
                    }
                }
                
                function refreshAll() {
                    loadSystemStatus();
                    loadEvents();
                    loadRecommendations();
                }
                
                // 页面加载时初始化
                window.onload = function() {
                    refreshAll();
                    // 每30秒自动刷新状态
                    setInterval(loadSystemStatus, 30000);
                };
            </script>
        </body>
        </html>
        """
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """启动服务器
        
        Args:
            host: 监听地址
            port: 监听端口
        """
        await self.api.start_server(host, port)


def create_static_server(config_path: str = "config/config.yaml") -> StaticFileServer:
    """创建静态文件服务器
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        StaticFileServer: 服务器实例
    """
    return StaticFileServer(config_path)
