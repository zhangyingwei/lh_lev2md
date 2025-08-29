# 开发者指南

## 🏗️ 开发环境搭建

### 开发工具要求
- Python 3.8+
- uv 包管理器
- Git
- VS Code (推荐) 或其他IDE
- Redis (可选，用于缓存)

### 开发环境配置
```bash
# 1. 克隆项目
git clone https://github.com/zhangyingwei/lh_lev2md.git
cd lh_lev2md

# 2. 安装开发依赖
uv sync --dev

# 3. 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 4. 安装pre-commit钩子
uv run pre-commit install
```

## 📁 项目架构详解

### 目录结构说明
```
src/trading_system/
├── __init__.py              # 包入口，定义版本和主要导出
├── main.py                  # 系统主入口，命令行接口
├── config/                  # 配置管理模块
│   ├── __init__.py
│   └── config_manager.py    # YAML配置文件管理器
├── models/                  # 数据模型层
│   ├── __init__.py
│   ├── base.py              # SQLAlchemy基础模型和数据库管理
│   ├── stock_data.py        # 股票和Level2数据模型
│   ├── scoring_data.py      # 评分和交易信号模型
│   ├── data_lifecycle.py    # 数据生命周期管理
│   └── database_init.py     # 数据库初始化脚本
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── logger.py            # 日志系统配置
│   └── exceptions.py        # 自定义异常和装饰器
├── data/                    # 数据接收层 (待开发)
├── engines/                 # 计算引擎层 (待开发)
└── strategies/              # 策略执行层 (待开发)
```

### 模块设计原则
1. **分层架构**: 数据层 → 引擎层 → 策略层 → 应用层
2. **单一职责**: 每个模块专注特定功能
3. **依赖注入**: 通过配置管理器注入依赖
4. **异常处理**: 统一的异常处理机制
5. **日志记录**: 结构化日志和性能监控

## 🔧 开发工作流

### 代码开发流程
```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发代码
# 编写代码...

# 3. 代码质量检查
uv run black src/                    # 格式化代码
uv run ruff check src/               # 代码检查
uv run mypy src/                     # 类型检查

# 4. 运行测试
uv run pytest tests/                 # 单元测试
uv run pytest --cov=src/            # 覆盖率测试

# 5. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 6. 推送分支
git push origin feature/new-feature
```

### Git提交规范
使用 Conventional Commits 格式：
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**类型说明**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

**示例**:
```bash
feat(scoring): 添加涨停炸板评分算法
fix(database): 修复SQLite连接池问题
docs(readme): 更新安装指南
```

## 🧪 测试指南

### 测试结构
```
tests/
├── __init__.py
├── conftest.py              # pytest配置和fixtures
├── test_config/             # 配置模块测试
├── test_models/             # 数据模型测试
├── test_utils/              # 工具模块测试
└── integration/             # 集成测试
```

### 编写测试
```python
# tests/test_models/test_stock_data.py
import pytest
from decimal import Decimal
from datetime import date
from trading_system.models import StockInfo, db_manager

class TestStockInfo:
    """股票信息模型测试"""
    
    def test_create_stock_info(self):
        """测试创建股票信息"""
        stock = StockInfo(
            stock_code="000001",
            stock_name="平安银行",
            market="SZ",
            float_market_value=Decimal("25000000")
        )
        
        assert stock.stock_code == "000001"
        assert stock.stock_name == "平安银行"
        assert stock.market == "SZ"
    
    def test_stock_info_to_dict(self):
        """测试转换为字典"""
        stock = StockInfo(
            stock_code="000001",
            stock_name="平安银行",
            market="SZ"
        )
        
        data = stock.to_dict()
        assert data["stock_code"] == "000001"
        assert data["stock_name"] == "平安银行"
```

### 运行测试
```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_models/test_stock_data.py

# 运行特定测试方法
uv run pytest tests/test_models/test_stock_data.py::TestStockInfo::test_create_stock_info

# 生成覆盖率报告
uv run pytest --cov=src/trading_system --cov-report=html
```

## 📊 数据库开发

### 添加新数据模型
```python
# 1. 在models/目录下创建新模型文件
# src/trading_system/models/new_model.py

from sqlalchemy import Column, String, Integer, DateTime
from .base import BaseModel

class NewModel(BaseModel):
    """新数据模型"""
    __tablename__ = 'new_table'
    
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<NewModel(name={self.name}, value={self.value})>"

# 2. 在models/__init__.py中导出
from .new_model import NewModel
__all__.append("NewModel")

# 3. 创建迁移脚本（如果需要）
# 4. 编写测试
```

### 数据库迁移
```python
# 简单的迁移脚本示例
def migrate_database():
    """数据库迁移"""
    from trading_system.models.base import db_manager
    from sqlalchemy import text
    
    session = db_manager.get_session()
    try:
        # 添加新列
        session.execute(text("ALTER TABLE stock_info ADD COLUMN new_field TEXT"))
        session.commit()
        print("迁移完成")
    except Exception as e:
        session.rollback()
        print(f"迁移失败: {e}")
    finally:
        session.close()
```

## 🔌 添加新功能模块

### 创建新引擎模块
```python
# src/trading_system/engines/new_engine.py

from typing import List, Dict, Any
from ..utils.logger import get_logger
from ..utils.exceptions import CalculationException

class NewEngine:
    """新计算引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger('new_engine')
    
    def calculate(self, data: List[Dict]) -> List[Dict]:
        """计算逻辑"""
        try:
            results = []
            for item in data:
                result = self._process_item(item)
                results.append(result)
            return results
        except Exception as e:
            self.logger.error(f"计算失败: {e}")
            raise CalculationException(f"新引擎计算失败: {e}")
    
    def _process_item(self, item: Dict) -> Dict:
        """处理单个项目"""
        # 具体计算逻辑
        return item
```

### 集成到主系统
```python
# src/trading_system/main.py 中添加

from .engines.new_engine import NewEngine

class TradingSystem:
    def __init__(self, config_path: str):
        # ... 现有代码 ...
        self.new_engine = None
    
    async def _initialize_components(self):
        """初始化系统组件"""
        # ... 现有代码 ...
        
        # 初始化新引擎
        engine_config = self.config.get('new_engine', {})
        self.new_engine = NewEngine(engine_config)
        self.components['new_engine'] = self.new_engine
```

## 📝 文档编写

### 代码文档规范
```python
def complex_function(param1: str, param2: int, param3: Optional[Dict] = None) -> List[str]:
    """复杂函数的文档字符串示例
    
    这里是函数的详细描述，说明函数的作用和用途。
    
    Args:
        param1: 第一个参数的描述
        param2: 第二个参数的描述，必须是正整数
        param3: 第三个参数的描述，可选参数
        
    Returns:
        List[str]: 返回值的描述，字符串列表
        
    Raises:
        ValueError: 当param2不是正整数时抛出
        CalculationException: 当计算过程出错时抛出
        
    Example:
        >>> result = complex_function("test", 10, {"key": "value"})
        >>> print(result)
        ['result1', 'result2']
        
    Note:
        这里是一些重要的注意事项或使用说明。
    """
    # 函数实现...
    pass
```

### API文档生成
```bash
# 使用Sphinx生成文档
uv add --dev sphinx sphinx-rtd-theme

# 初始化文档
sphinx-quickstart docs

# 生成API文档
sphinx-apidoc -o docs/source src/trading_system

# 构建文档
cd docs && make html
```

## 🚀 部署指南

### 开发环境部署
```bash
# 1. 设置环境变量
export TRADING_ENV=development
export LOG_LEVEL=DEBUG

# 2. 启动开发服务
uv run python -m trading_system.main --debug

# 3. 启动Redis (如果需要)
redis-server
```

### 生产环境部署
```bash
# 1. 创建生产配置
cp config/config.yaml config/prod_config.yaml
# 编辑生产配置...

# 2. 设置环境变量
export TRADING_ENV=production
export LOG_LEVEL=INFO

# 3. 启动生产服务
uv run trading-system --config config/prod_config.yaml
```

## 🔍 调试技巧

### 日志调试
```python
from trading_system.utils.logger import get_logger

logger = get_logger('debug')

# 不同级别的日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")

# 记录异常
try:
    # 可能出错的代码
    pass
except Exception as e:
    logger.error(f"操作失败: {e}", exc_info=True)
```

### 性能分析
```python
import time
from functools import wraps

def timing_decorator(func):
    """性能计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} 执行时间: {end_time - start_time:.4f}秒")
        return result
    return wrapper

@timing_decorator
def slow_function():
    """需要性能分析的函数"""
    time.sleep(1)
    return "完成"
```

## 📋 代码审查清单

### 提交前检查
- [ ] 代码格式化 (black)
- [ ] 代码检查 (ruff)
- [ ] 类型检查 (mypy)
- [ ] 单元测试通过
- [ ] 测试覆盖率 > 80%
- [ ] 文档字符串完整
- [ ] 配置文件更新
- [ ] 变更日志更新

### 代码质量标准
- 函数长度 < 50行
- 类长度 < 500行
- 圈复杂度 < 10
- 重复代码 < 5%
- 注释覆盖率 > 20%

## 🤝 贡献流程

1. **Fork项目** → 创建个人分支
2. **创建功能分支** → `git checkout -b feature/amazing-feature`
3. **开发功能** → 遵循代码规范
4. **编写测试** → 确保测试覆盖率
5. **提交代码** → 遵循提交规范
6. **创建PR** → 详细描述变更内容
7. **代码审查** → 响应审查意见
8. **合并代码** → 完成贡献

---

**💡 开发提示**: 
- 优先编写测试，然后实现功能 (TDD)
- 保持代码简洁，遵循SOLID原则
- 及时更新文档，方便团队协作
- 定期重构代码，保持代码质量
