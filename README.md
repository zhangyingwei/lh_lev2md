# 股票自动交易系统

基于Level2行情的股票自动交易系统，支持历史评分计算、股票池筛选和实时买入策略。

## 📋 项目概述

本系统是一个完整的股票自动交易解决方案，具备以下核心功能：

- **Level2行情接收**: 基于lev2mdapi的实时行情数据接收
- **历史评分引擎**: 6种评分算法（涨停炸板、跌幅、封单、时间、连续跌幅、回封）
- **股票池筛选**: A、B、ZB三类股票池的智能筛选
- **买入策略**: 4种实时买入策略实现
- **风险管理**: 完善的风控和监控告警机制

## 🏗️ 技术架构

### 核心技术栈
- **编程语言**: Python 3.8+
- **包管理**: uv (高性能包管理器)
- **数据存储**: SQLite + Redis
- **数据处理**: pandas, numpy, ta-lib
- **行情接口**: lev2mdapi
- **配置管理**: YAML
- **日志系统**: loguru

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Level2行情    │    │   历史评分引擎   │    │   股票池筛选    │
│   数据接收      │───▶│   6种算法       │───▶│   A/B/ZB池      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   实时数据处理   │    │   买入策略引擎   │    │   风险管理      │
│   SQLite存储    │───▶│   4种策略       │───▶│   监控告警      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- Windows/Linux/macOS
- 至少 4GB 内存
- 至少 10GB 磁盘空间

### 安装步骤

#### 1. 安装uv包管理器

**Windows (PowerShell)**:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. 克隆项目
```bash
git clone https://github.com/your-repo/trading-system.git
cd trading-system
```

#### 3. 安装依赖
```bash
# 同步依赖（自动创建虚拟环境）
uv sync

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

#### 4. 初始化数据库
```bash
# 初始化数据库和创建示例数据
uv run python -m trading_system.models.database_init
```

#### 5. 配置系统
编辑 `config/config.yaml` 文件，配置您的参数：

```yaml
# Level2行情配置
level2:
  connection_mode: "tcp"
  tcp_address: "tcp://127.0.0.1:6900"
  user_id: "your_user_id"
  password: "your_password"

# 风控参数
risk_management:
  total_capital: 1000000        # 总资金(100万)
  max_position_ratio: 0.1       # 单股最大仓位比例(10%)
  max_daily_loss: 0.05          # 单日最大亏损比例(5%)
```

### 运行系统

#### 启动完整系统
```bash
# 启动交易系统
uv run trading-system

# 或者使用Python模块方式
uv run python -m trading_system.main
```

#### 开发模式运行
```bash
# 启用调试模式
uv run trading-system --debug

# 指定配置文件
uv run trading-system --config config/dev_config.yaml
```

## 📖 使用指南

### 配置说明

系统配置文件位于 `config/config.yaml`，主要配置项包括：

#### 数据库配置
```yaml
database:
  sqlite:
    path: "data/trading_system.db"    # SQLite数据库路径
    echo: false                       # 是否显示SQL语句
  redis:
    host: "localhost"                 # Redis主机
    port: 6379                        # Redis端口
    db: 0                            # Redis数据库编号
```

#### Level2行情配置
```yaml
level2:
  connection_mode: "tcp"              # 连接模式: tcp/multicast
  tcp_address: "tcp://127.0.0.1:6900" # TCP地址
  user_id: ""                         # 用户ID
  password: ""                        # 密码
  max_reconnect_attempts: 10          # 最大重连次数
  reconnect_interval: 5               # 重连间隔(秒)
```

#### 评分算法参数
```yaml
scoring_parameters:
  x1_percent: 0.05                    # 涨停炸板评分系数
  x2_percent: 0.03                    # 跌幅评分系数
  x3_percent: 0.04                    # 连续跌幅评分系数
  decline_threshold: -0.02            # 跌幅阈值
  limit_up_seal_threshold: 30000000   # 涨停封单阈值(3000万)
  reseal_count_threshold: 5           # 回封次数阈值
```

### 数据管理

#### 查看数据库状态
```bash
# 查看表统计信息
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager()
stats = manager.get_table_statistics()
print('表统计信息:', stats)
print('数据库大小:', manager.get_database_size(), 'MB')
"
```

#### 手动清理数据
```bash
# 清理超过7天的数据
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager(retention_days=7)
result = manager.cleanup_old_data()
print('清理结果:', result)
"
```

#### 备份数据库
```bash
# 备份数据库
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager()
backup_path = manager.backup_database()
print('备份完成:', backup_path)
"
```

## 🔧 开发指南

### 项目结构
```
trading_system/
├── src/trading_system/              # 源代码
│   ├── __init__.py                  # 包初始化
│   ├── main.py                      # 主入口
│   ├── config/                      # 配置管理
│   │   ├── __init__.py
│   │   └── config_manager.py
│   ├── models/                      # 数据模型
│   │   ├── __init__.py
│   │   ├── base.py                  # 基础模型
│   │   ├── stock_data.py            # 股票数据模型
│   │   ├── scoring_data.py          # 评分数据模型
│   │   ├── data_lifecycle.py        # 数据生命周期
│   │   └── database_init.py         # 数据库初始化
│   ├── utils/                       # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py                # 日志系统
│   │   └── exceptions.py            # 异常处理
│   ├── data/                        # 数据层(待开发)
│   ├── engines/                     # 计算引擎(待开发)
│   └── strategies/                  # 策略模块(待开发)
├── config/                          # 配置文件
│   └── config.yaml                  # 主配置文件
├── data/                            # 数据目录
│   └── trading_system.db            # SQLite数据库
├── logs/                            # 日志目录
├── tests/                           # 测试代码
├── pyproject.toml                   # 项目配置
├── uv.lock                          # 依赖锁定文件
└── README.md                        # 项目文档
```

### 代码规范

项目使用以下代码质量工具：

```bash
# 代码格式化
uv run black src/

# 代码检查
uv run ruff check src/

# 类型检查
uv run mypy src/

# 运行测试
uv run pytest tests/
```

### 添加新功能

1. **创建新模块**: 在相应目录下创建Python文件
2. **编写测试**: 在tests目录下创建对应的测试文件
3. **更新配置**: 如需要，更新config.yaml配置
4. **运行测试**: 确保所有测试通过
5. **提交代码**: 遵循Git提交规范

### 数据模型说明

#### 核心数据表

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `stock_info` | 股票基础信息 | stock_code, stock_name, market, float_market_value |
| `daily_quote` | 日线行情数据 | stock_code, trade_date, open_price, close_price, volume |
| `level2_snapshots` | Level2快照行情 | stock_code, timestamp, last_price, bid/ask五档 |
| `level2_transactions` | Level2逐笔成交 | stock_code, timestamp, price, volume, trade_type |
| `level2_order_details` | Level2逐笔委托 | stock_code, timestamp, order_no, price, volume, side |
| `historical_scores` | 历史评分结果 | stock_code, trade_date, 各种评分字段, total_score |
| `stock_pool_results` | 股票池筛选结果 | stock_code, trade_date, pool_type, selection_reason |
| `trading_signals` | 交易信号 | stock_code, signal_time, signal_type, strategy_name |
| `system_metrics` | 系统监控指标 | metric_time, metric_type, metric_value, is_alert |

#### 数据生命周期

- **保留期**: 默认7天，可配置
- **清理策略**: 每日凌晨2点自动清理
- **备份机制**: 支持手动和自动备份
- **优化策略**: 自动VACUUM和索引优化

## 📊 监控与运维

### 日志管理

系统日志位于 `logs/trading_system.log`，支持：
- 自动轮转（每日或按大小）
- 多级别日志（DEBUG/INFO/WARNING/ERROR）
- 结构化日志格式

```bash
# 查看实时日志
tail -f logs/trading_system.log

# 查看错误日志
grep "ERROR" logs/trading_system.log

# 查看最近100行日志
tail -n 100 logs/trading_system.log
```

### 性能监控

系统内置性能监控，包括：
- CPU和内存使用率
- 数据库查询性能
- 网络连接状态
- 处理延迟统计

```bash
# 查看系统性能指标
uv run python -c "
from trading_system.models import SystemMetrics, db_manager
session = db_manager.get_session()
metrics = session.query(SystemMetrics).order_by(SystemMetrics.metric_time.desc()).limit(10).all()
for metric in metrics:
    print(f'{metric.metric_time}: {metric.metric_name} = {metric.metric_value} {metric.metric_unit}')
session.close()
"
```

### 告警机制

支持多种告警方式：
- 日志告警
- 系统指标告警
- 业务逻辑告警

告警阈值配置：
```yaml
monitoring:
  alert_thresholds:
    cpu_usage: 80.0           # CPU使用率告警阈值
    memory_usage: 85.0        # 内存使用率告警阈值
    disk_usage: 90.0          # 磁盘使用率告警阈值
    queue_size: 5000          # 队列大小告警阈值
    processing_latency: 1.0   # 处理延迟告警阈值(秒)
```

## 🧪 测试指南

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_models.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=src/trading_system --cov-report=html

# 运行测试并显示详细输出
uv run pytest -v
```

### 测试数据库

```bash
# 测试数据库连接
uv run python -c "
from trading_system.models.database_init import test_database_connection
result = test_database_connection()
print('测试结果:', result)
"

# 测试数据生命周期管理
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager()
stats = manager.get_table_statistics()
print('表统计:', stats)
"
```

## ❓ 常见问题

### Q: 如何更改数据保留期？
A: 修改config.yaml中的相关参数，或在DataLifecycleManager中指定retention_days参数。

### Q: 数据库文件过大怎么办？
A: 执行手动清理命令或调整数据保留期。系统会自动执行VACUUM优化。
```bash
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager(retention_days=3)  # 改为3天
result = manager.cleanup_old_data()
print('清理结果:', result)
"
```

### Q: 如何添加新的评分算法？
A: 在engines模块中创建新的评分类，继承基础评分接口。

### Q: 系统支持多账户吗？
A: 当前版本支持单账户，多账户功能在后续版本中提供。

### Q: 如何修改日志级别？
A: 修改config.yaml中的logging.level配置：
```yaml
logging:
  level: "DEBUG"  # DEBUG/INFO/WARNING/ERROR
```

### Q: Redis连接失败怎么办？
A: 检查Redis服务是否启动，确认配置文件中的连接参数正确。

### Q: 如何重置数据库？
A: 删除数据库文件后重新初始化：
```bash
rm data/trading_system.db
uv run python -m trading_system.models.database_init
```

## 🔧 故障排除

### 常见错误及解决方案

#### 1. 依赖安装失败
```bash
# 清理缓存重新安装
uv cache clean
uv sync --reinstall
```

#### 2. 数据库连接错误
```bash
# 检查数据库文件权限
ls -la data/trading_system.db

# 重新初始化数据库
uv run python -m trading_system.models.database_init
```

#### 3. 配置文件错误
```bash
# 验证YAML语法
uv run python -c "
import yaml
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print('配置文件语法正确')
"
```

#### 4. 内存使用过高
- 调整batch_size参数
- 增加数据清理频率
- 检查是否有内存泄漏

#### 5. 性能问题
- 检查数据库索引
- 调整SQLite配置参数
- 监控系统资源使用

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 开发规范

- 遵循PEP 8代码风格
- 添加适当的类型注解
- 编写单元测试
- 更新相关文档

## 📞 支持与联系

- 项目主页: https://github.com/zhangyingwei/lh_lev2md
- 问题反馈: https://github.com/zhangyingwei/lh_lev2md/issues
- 邮箱: ai@trading-system.com

## 📈 版本历史

### v1.0.0 (2025-01-21)
- ✅ 完成项目基础架构搭建
- ✅ 实现SQLite数据模型和1周滚动存储
- ✅ 配置uv包管理和开发环境
- ✅ 建立完整的配置管理和日志系统
- 🚧 Level2数据接收模块开发中

---

**⚠️ 风险提示**: 本系统仅供学习和研究使用，实际交易请谨慎评估风险。投资有风险，入市需谨慎。