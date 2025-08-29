# 量化交易系统部署指南

## 概述

本文档提供量化交易系统的完整部署指南，包括环境搭建、系统配置、部署流程、监控告警和故障排除。

## 系统要求

### 硬件要求
- **CPU**: 4核心以上，推荐8核心
- **内存**: 8GB以上，推荐16GB
- **存储**: 50GB可用空间，推荐SSD
- **网络**: 稳定的互联网连接，低延迟

### 软件要求
- **操作系统**: Windows 10/11, Ubuntu 20.04+, CentOS 8+
- **Python**: 3.8+，推荐3.11+
- **uv**: 最新版本包管理器
- **数据库**: SQLite（内置）或PostgreSQL（可选）

## 环境搭建

### 1. 安装Python和uv

#### Windows
```bash
# 安装Python 3.11
# 从 https://python.org 下载安装

# 安装uv
pip install uv
```

#### Linux/macOS
```bash
# 安装Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv

# 安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆项目
```bash
git clone <repository-url>
cd lh_lev2md
```

### 3. 环境配置
```bash
# 创建虚拟环境并安装依赖
uv sync

# 验证安装
uv run python --version
```

## 配置管理

### 主配置文件 (config/config.yaml)

```yaml
# Level2行情配置
level2:
  tcp_address: "tcp://127.0.0.1:6402"
  multicast_address: "udp://233.50.50.50:6500"
  username: "your_username"
  password: "your_password"
  connection_mode: "tcp"  # tcp 或 multicast

# 数据库配置
database:
  sqlite:
    path: "data/trading_system.db"
    pool_size: 10
    echo: false

# 算法配置
algorithms:
  detector:
    limit_up_threshold: 0.095
    price_tolerance: 0.001
    min_limit_duration: 30
    break_threshold: 0.02
  scorer:
    duration_weight: 0.25
    volume_weight: 0.30
    price_stability_weight: 0.20
    break_intensity_weight: 0.25

# 性能配置
performance:
  max_workers: 4
  queue_size: 10000
  batch_size: 100
  cache_size: 1000

# 日志配置
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/trading_system.log"
  max_size: "100MB"
  backup_count: 5
```

## 部署流程

### 1. 自动部署（推荐）

```bash
# 完整部署
python scripts/deploy.py deploy --mode api

# 部署选项
python scripts/deploy.py deploy --mode web --skip-tests
```

### 2. 手动部署

#### 步骤1: 环境检查
```bash
python scripts/deploy.py status
```

#### 步骤2: 安装依赖
```bash
uv sync
```

#### 步骤3: 数据库初始化
```bash
uv run python -c "
from src.trading_system.models.database_init import initialize_database
initialize_database('sqlite:///data/trading_system.db')
print('数据库初始化完成')
"
```

#### 步骤4: 运行测试
```bash
python scripts/deploy.py test
```

#### 步骤5: 启动系统
```bash
# API模式
python scripts/deploy.py start --mode api

# Web模式
python scripts/deploy.py start --mode web

# 服务模式
python scripts/deploy.py start --mode service
```

## 启动模式

### 1. API模式
- **用途**: 提供RESTful API接口
- **端口**: 8000
- **访问**: http://localhost:8000
- **文档**: http://localhost:8000/docs

### 2. Web模式
- **用途**: 提供完整的Web界面
- **端口**: 8000
- **访问**: http://localhost:8000/web
- **仪表板**: http://localhost:8000/dashboard

### 3. 服务模式
- **用途**: 后台服务，无Web界面
- **功能**: 数据处理和算法计算
- **监控**: 通过日志文件

## 监控告警

### 1. 系统监控

#### 性能指标
- **CPU使用率**: < 80%
- **内存使用率**: < 85%
- **磁盘使用率**: < 90%
- **网络延迟**: < 100ms

#### 业务指标
- **数据接收率**: > 95%
- **事件检测率**: 实时
- **推荐生成时间**: < 500ms
- **系统可用性**: > 99.5%

### 2. 日志监控

#### 日志级别
- **ERROR**: 系统错误，需要立即处理
- **WARNING**: 警告信息，需要关注
- **INFO**: 一般信息，正常运行
- **DEBUG**: 调试信息，开发使用

#### 关键日志
```bash
# 查看错误日志
tail -f logs/trading_system.log | grep ERROR

# 查看系统状态
tail -f logs/trading_system.log | grep "系统统计"

# 查看性能指标
tail -f logs/trading_system.log | grep "性能监控"
```

### 3. 告警配置

#### 告警规则
```yaml
alerts:
  system_down:
    condition: "系统停止运行"
    severity: "critical"
    action: "立即重启"
  
  high_cpu:
    condition: "CPU使用率 > 80%"
    severity: "warning"
    action: "性能优化"
  
  data_loss:
    condition: "数据接收中断 > 5分钟"
    severity: "critical"
    action: "检查网络连接"
  
  low_performance:
    condition: "推荐生成时间 > 1秒"
    severity: "warning"
    action: "算法优化"
```

## 测试策略

### 1. 单元测试

#### 测试覆盖
- **数据模型**: 100%
- **算法模块**: 95%
- **API接口**: 90%
- **Web界面**: 85%

#### 运行测试
```bash
# 运行所有测试
python scripts/deploy.py test

# 运行特定模块测试
uv run python -m src.trading_system.algorithms.test_limit_up_analyzer
uv run python -m src.trading_system.api.test_web_api
```

### 2. 集成测试

#### 测试场景
- **数据流测试**: Level2数据接收→算法处理→结果输出
- **API集成测试**: 前端→API→后端服务
- **性能测试**: 高并发数据处理
- **故障恢复测试**: 网络中断、系统重启

### 3. 压力测试

#### 测试指标
- **数据处理能力**: 1000条/秒
- **并发用户数**: 100个
- **响应时间**: < 100ms
- **系统稳定性**: 24小时连续运行

## 故障排除

### 1. 常见问题

#### 系统无法启动
```bash
# 检查环境
python scripts/deploy.py status

# 检查配置文件
cat config/config.yaml

# 检查日志
tail -n 50 logs/trading_system.log
```

#### 数据接收异常
```bash
# 检查网络连接
ping <level2_server>

# 检查认证信息
grep "登录" logs/trading_system.log

# 重启数据服务
python scripts/deploy.py restart --mode service
```

#### 性能问题
```bash
# 检查系统资源
top
df -h

# 检查数据库
sqlite3 data/trading_system.db ".schema"

# 优化配置
vim config/config.yaml
```

### 2. 错误代码

| 错误代码 | 描述 | 解决方案 |
|---------|------|----------|
| E001 | 配置文件错误 | 检查YAML格式 |
| E002 | 数据库连接失败 | 检查数据库文件 |
| E003 | Level2连接失败 | 检查网络和认证 |
| E004 | 算法计算异常 | 检查输入数据 |
| E005 | API服务异常 | 检查端口占用 |

### 3. 性能优化

#### 系统优化
- **增加工作线程数**: 修改max_workers配置
- **调整缓存大小**: 修改cache_size配置
- **优化数据库**: 添加索引，定期清理
- **网络优化**: 使用UDP组播模式

#### 算法优化
- **批量处理**: 增加batch_size
- **并行计算**: 启用多进程
- **缓存策略**: 优化缓存命中率
- **内存管理**: 及时释放资源

## 维护指南

### 1. 日常维护

#### 每日检查
- 系统运行状态
- 日志文件大小
- 数据库性能
- 网络连接状态

#### 每周维护
- 清理过期数据
- 备份配置文件
- 更新依赖包
- 性能分析报告

### 2. 数据备份

#### 备份策略
```bash
# 数据库备份
cp data/trading_system.db backup/trading_system_$(date +%Y%m%d).db

# 配置备份
tar -czf backup/config_$(date +%Y%m%d).tar.gz config/

# 日志备份
tar -czf backup/logs_$(date +%Y%m%d).tar.gz logs/
```

### 3. 版本升级

#### 升级流程
1. 备份当前系统
2. 下载新版本
3. 更新依赖
4. 运行测试
5. 平滑切换
6. 验证功能

## 安全配置

### 1. 网络安全
- 使用防火墙限制访问
- 配置SSL/TLS加密
- 定期更新安全补丁

### 2. 数据安全
- 敏感信息加密存储
- 定期备份重要数据
- 访问权限控制

### 3. 系统安全
- 最小权限原则
- 定期安全审计
- 异常行为监控

## 联系支持

如遇到问题，请提供以下信息：
- 系统版本和配置
- 错误日志和截图
- 问题复现步骤
- 系统环境信息
