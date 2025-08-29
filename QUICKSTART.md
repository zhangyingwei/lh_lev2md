# 快速开始指南

## 🚀 5分钟快速部署

### 1. 环境准备
```bash
# 确保已安装Python 3.8+
python --version

# 安装uv包管理器 (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或者 (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 项目部署
```bash
# 克隆项目
git clone https://github.com/zhangyingwei/lh_lev2md.git
cd lh_lev2md

# 一键安装依赖
uv sync

# 初始化数据库
uv run python -m trading_system.models.database_init
```

### 3. 验证安装
```bash
# 测试项目导入
uv run python -c "import trading_system; print('✅ 安装成功:', trading_system.__version__)"

# 测试数据库
uv run python -c "
from trading_system.models.database_init import test_database_connection
result = test_database_connection()
print('✅ 数据库连接:', '成功' if result['connection_success'] else '失败')
print('✅ 创建表数量:', result.get('table_count', 0))
"
```

## ⚡ 常用命令

### 数据管理
```bash
# 查看数据库状态
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager()
print('📊 数据库大小:', f'{manager.get_database_size():.2f} MB')
stats = manager.get_table_statistics()
for table, info in stats.items():
    print(f'📋 {table}: {info[\"count\"]} 条记录')
"

# 清理旧数据
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager(retention_days=7)
result = manager.cleanup_old_data()
total = sum(result.values())
print(f'🧹 清理完成，删除 {total} 条记录')
"

# 备份数据库
uv run python -c "
from trading_system.models import DataLifecycleManager
manager = DataLifecycleManager()
backup_path = manager.backup_database()
print(f'💾 备份完成: {backup_path}')
"
```

### 开发工具
```bash
# 代码格式化
uv run black src/

# 代码检查
uv run ruff check src/

# 运行测试
uv run pytest

# 查看依赖
uv tree
```

### 系统运行
```bash
# 启动系统（开发模式）
uv run python -m trading_system.main --debug

# 启动系统（生产模式）
uv run trading-system

# 指定配置文件
uv run trading-system --config config/prod_config.yaml
```

## 🔧 配置快速修改

### 修改数据保留期
```bash
# 编辑配置文件
# 在 config/config.yaml 中添加或修改：
# data_retention_days: 3  # 改为3天
```

### 修改日志级别
```bash
# 在 config/config.yaml 中修改：
# logging:
#   level: "DEBUG"  # 改为DEBUG级别
```

### 修改数据库路径
```bash
# 在 config/config.yaml 中修改：
# database:
#   sqlite:
#     path: "data/my_trading.db"  # 自定义路径
```

## 📊 系统状态检查

### 一键健康检查
```bash
uv run python -c "
print('🔍 系统健康检查')
print('=' * 50)

# 检查项目导入
try:
    import trading_system
    print('✅ 项目导入: 正常')
    print(f'   版本: {trading_system.__version__}')
except Exception as e:
    print(f'❌ 项目导入: 失败 - {e}')

# 检查数据库
try:
    from trading_system.models.database_init import test_database_connection
    result = test_database_connection()
    if result['connection_success']:
        print('✅ 数据库连接: 正常')
        print(f'   表数量: {result[\"table_count\"]}')
    else:
        print(f'❌ 数据库连接: 失败 - {result.get(\"error\", \"未知错误\")}')
except Exception as e:
    print(f'❌ 数据库连接: 异常 - {e}')

# 检查配置文件
try:
    from trading_system.config import ConfigManager
    config_manager = ConfigManager('config/config.yaml')
    config = config_manager.get_config()
    print('✅ 配置文件: 正常')
    print(f'   系统名称: {config.get(\"system\", {}).get(\"name\", \"未知\")}')
except Exception as e:
    print(f'❌ 配置文件: 异常 - {e}')

# 检查数据库大小
try:
    from trading_system.models import DataLifecycleManager
    manager = DataLifecycleManager()
    size = manager.get_database_size()
    print(f'📊 数据库大小: {size:.2f} MB')
    if size > 100:
        print('⚠️  数据库较大，建议清理旧数据')
except Exception as e:
    print(f'❌ 数据库大小检查: 异常 - {e}')

print('=' * 50)
print('🎉 健康检查完成')
"
```

## 🆘 故障快速修复

### 重置环境
```bash
# 清理并重新安装
uv cache clean
rm -rf .venv
uv sync

# 重新初始化数据库
rm data/trading_system.db
uv run python -m trading_system.models.database_init
```

### 依赖问题
```bash
# 查看依赖冲突
uv tree

# 强制重新安装
uv sync --reinstall

# 更新依赖
uv lock --upgrade
```

### 权限问题
```bash
# Windows: 以管理员身份运行PowerShell
# Linux/macOS: 检查文件权限
chmod 755 data/
chmod 644 data/trading_system.db
```

## 📱 快速联系

- 🐛 问题反馈: [GitHub Issues](https://github.com/zhangyingwei/lh_lev2md/issues)
- 📧 邮箱支持: ai@trading-system.com
- 📖 完整文档: [README.md](README.md)

---
**💡 提示**: 如果遇到问题，请先运行健康检查命令，大部分问题都能快速定位和解决。
