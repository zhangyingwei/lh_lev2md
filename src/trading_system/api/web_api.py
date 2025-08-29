"""
Web API接口

提供RESTful API接口，包括数据查询、推荐获取和系统监控功能
基于FastAPI框架实现高性能异步API服务
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ..services import TradingSystemService, create_trading_service
from ..algorithms import LimitUpBreakEvent, StockRecommendation
from ..utils.logger import get_logger


# API响应模型
class APIResponse(BaseModel):
    """API统一响应格式"""
    success: bool = True
    message: str = "操作成功"
    data: Any = None
    timestamp: datetime = Field(default_factory=datetime.now)


class EventResponse(BaseModel):
    """炸板事件响应模型"""
    stock_code: str
    break_time: datetime
    limit_up_price: float
    break_price: float
    break_volume: int
    break_amount: float
    duration_seconds: int
    score: float
    price_volatility: float


class RecommendationResponse(BaseModel):
    """推荐响应模型"""
    rank: int
    stock_code: str
    current_price: float
    total_score: float
    recommendation_reason: str
    risk_level: str
    confidence: float
    break_events_count: int


class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    is_running: bool
    start_time: Optional[datetime]
    uptime_seconds: int
    data_service_status: str
    compute_engine_status: str
    total_data_processed: int
    total_events_detected: int
    total_recommendations: int


class TradingSystemAPI:
    """量化交易系统API服务"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化API服务
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.logger = get_logger('trading_api')
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title="量化交易系统API",
            description="基于Level2行情数据的涨停炸板分析系统",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # 配置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 交易系统服务
        self.trading_service: Optional[TradingSystemService] = None
        
        # 注册路由
        self._register_routes()
        
        # 注册事件处理器
        self._register_event_handlers()
        
        self.logger.info("量化交易系统API初始化完成")
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/", response_model=APIResponse)
        async def root():
            """根路径"""
            return APIResponse(
                message="量化交易系统API服务运行中",
                data={"version": "1.0.0", "status": "running"}
            )
        
        @self.app.get("/health", response_model=APIResponse)
        async def health_check():
            """健康检查"""
            if not self.trading_service:
                raise HTTPException(status_code=503, detail="交易系统服务未启动")
            
            status = self.trading_service.get_system_status()
            return APIResponse(
                message="系统健康",
                data={"is_running": status.is_running}
            )
        
        @self.app.post("/system/start", response_model=APIResponse)
        async def start_system():
            """启动交易系统"""
            if not self.trading_service:
                self.trading_service = create_trading_service(self.config_path)
            
            if self.trading_service.get_system_status().is_running:
                return APIResponse(message="系统已在运行中")
            
            success = await self.trading_service.start()
            if success:
                return APIResponse(message="系统启动成功")
            else:
                raise HTTPException(status_code=500, detail="系统启动失败")
        
        @self.app.post("/system/stop", response_model=APIResponse)
        async def stop_system():
            """停止交易系统"""
            if not self.trading_service:
                return APIResponse(message="系统未启动")
            
            success = await self.trading_service.stop()
            if success:
                return APIResponse(message="系统停止成功")
            else:
                raise HTTPException(status_code=500, detail="系统停止失败")
        
        @self.app.get("/system/status", response_model=APIResponse)
        async def get_system_status():
            """获取系统状态"""
            if not self.trading_service:
                raise HTTPException(status_code=503, detail="交易系统服务未初始化")
            
            status = self.trading_service.get_system_status()
            stats = self.trading_service.get_system_statistics()
            
            uptime_seconds = 0
            if status.start_time:
                uptime_seconds = int((datetime.now() - status.start_time).total_seconds())
            
            response_data = SystemStatusResponse(
                is_running=status.is_running,
                start_time=status.start_time,
                uptime_seconds=uptime_seconds,
                data_service_status=status.data_service_status,
                compute_engine_status=status.compute_engine_status,
                total_data_processed=status.total_data_processed,
                total_events_detected=status.total_events_detected,
                total_recommendations=status.total_recommendations
            )
            
            return APIResponse(
                message="获取系统状态成功",
                data=response_data.dict()
            )
        
        @self.app.get("/system/statistics", response_model=APIResponse)
        async def get_system_statistics():
            """获取系统统计信息"""
            if not self.trading_service:
                raise HTTPException(status_code=503, detail="交易系统服务未初始化")
            
            stats = self.trading_service.get_system_statistics()
            return APIResponse(
                message="获取系统统计成功",
                data=stats
            )
        
        @self.app.post("/data/subscribe", response_model=APIResponse)
        async def subscribe_stocks(stock_codes: List[str]):
            """订阅股票数据"""
            if not self.trading_service:
                raise HTTPException(status_code=503, detail="交易系统服务未启动")
            
            success = await self.trading_service.subscribe_stocks(stock_codes)
            if success:
                return APIResponse(
                    message="股票数据订阅成功",
                    data={"subscribed_stocks": stock_codes}
                )
            else:
                raise HTTPException(status_code=500, detail="股票数据订阅失败")
        
        @self.app.get("/events", response_model=APIResponse)
        async def get_events(
            limit: int = Query(50, ge=1, le=1000, description="返回数量限制"),
            stock_code: Optional[str] = Query(None, description="股票代码筛选"),
            hours: Optional[int] = Query(24, ge=1, le=168, description="时间范围（小时）")
        ):
            """获取炸板事件"""
            if not self.trading_service:
                raise HTTPException(status_code=503, detail="交易系统服务未启动")
            
            events = self.trading_service.get_latest_events(limit)
            
            # 时间筛选
            if hours:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                events = [e for e in events if e.break_time >= cutoff_time]
            
            # 股票代码筛选
            if stock_code:
                events = [e for e in events if e.stock_code == stock_code]
            
            # 转换为响应格式
            event_responses = []
            for event in events:
                event_response = EventResponse(
                    stock_code=event.stock_code,
                    break_time=event.break_time,
                    limit_up_price=float(event.limit_up_price),
                    break_price=float(event.break_price),
                    break_volume=event.break_volume,
                    break_amount=float(event.break_amount),
                    duration_seconds=event.duration_seconds,
                    score=event.score,
                    price_volatility=event.price_volatility
                )
                event_responses.append(event_response.dict())
            
            return APIResponse(
                message="获取炸板事件成功",
                data={
                    "events": event_responses,
                    "total_count": len(event_responses)
                }
            )
        
        @self.app.get("/recommendations", response_model=APIResponse)
        async def get_recommendations(
            limit: int = Query(20, ge=1, le=100, description="推荐数量限制"),
            filter_preset: Optional[str] = Query(None, description="筛选预设"),
            sort_preset: Optional[str] = Query(None, description="排序预设"),
            min_score: Optional[float] = Query(None, ge=0, le=100, description="最低评分")
        ):
            """获取股票推荐"""
            if not self.trading_service:
                raise HTTPException(status_code=503, detail="交易系统服务未启动")
            
            recommendations = self.trading_service.get_latest_recommendations(limit)
            
            # 评分筛选
            if min_score is not None:
                recommendations = [r for r in recommendations if r.total_score >= min_score]
            
            # 转换为响应格式
            rec_responses = []
            for i, rec in enumerate(recommendations):
                rec_response = RecommendationResponse(
                    rank=i + 1,
                    stock_code=rec.stock_code,
                    current_price=float(rec.current_price),
                    total_score=rec.total_score,
                    recommendation_reason=rec.recommendation_reason,
                    risk_level=rec.risk_level,
                    confidence=rec.confidence,
                    break_events_count=len(rec.break_events)
                )
                rec_responses.append(rec_response.dict())
            
            return APIResponse(
                message="获取股票推荐成功",
                data={
                    "recommendations": rec_responses,
                    "total_count": len(rec_responses)
                }
            )
        
        @self.app.get("/presets", response_model=APIResponse)
        async def get_presets():
            """获取可用的预设条件"""
            if not self.trading_service:
                raise HTTPException(status_code=503, detail="交易系统服务未启动")
            
            # 这里需要从股票筛选管理器获取预设
            presets = {
                "filters": {
                    "high_quality": "高质量炸板筛选",
                    "recent": "最近炸板筛选",
                    "active_trading": "活跃交易筛选",
                    "stable_price": "价格稳定筛选"
                },
                "sorts": {
                    "by_score": "按评分排序",
                    "by_time": "按时间排序",
                    "by_volume": "按成交量排序",
                    "comprehensive": "综合排序"
                }
            }
            
            return APIResponse(
                message="获取预设条件成功",
                data=presets
            )
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """应用启动事件"""
            self.logger.info("API服务启动")
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """应用关闭事件"""
            if self.trading_service:
                await self.trading_service.stop()
            self.logger.info("API服务关闭")
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """启动API服务器
        
        Args:
            host: 监听地址
            port: 监听端口
        """
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        self.logger.info(f"启动API服务器: http://{host}:{port}")
        await server.serve()


def create_web_api(config_path: str = "config/config.yaml") -> TradingSystemAPI:
    """创建Web API实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        TradingSystemAPI: API实例
    """
    return TradingSystemAPI(config_path)
