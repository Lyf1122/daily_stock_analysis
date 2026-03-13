# 敏感配置后端脱敏实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 后端 API 返回敏感配置字段时自动脱敏为 `******`，防止 API Key 明文泄露

**架构:** 在 `SystemConfigService.get_config()` 方法中，检查字段的 `is_sensitive` schema 标记，对敏感字段返回掩码值而非明文

**技术栈:** Python 3.11, FastAPI, Pydantic

---

## 任务分解

### Task 1: 确认敏感字段标记完整

**文件:**
- 读取: `src/utils/systemConfigI18n.ts` (前端 schema 定义)

**目的:** 确保所有敏感字段都已标记 `is_sensitive: true`

**检查步骤:**

1. 检查关键字段是否有 `is_sensitive` 标记：
   - `TAVILY_API_KEYS`
   - `SERPAPI_API_KEYS`
   - `BRAVE_API_KEYS`
   - `GEMINI_API_KEY`
   - `LITELLM_API_KEY`
   - `DEEPSEEK_API_KEY`

2. 如有缺失，添加标记：
```typescript
is_sensitive: true,
```

**预期结果:** 所有 API Key 类字段都标记为敏感

---

### Task 2: 修改 get_config 方法添加脱敏逻辑

**文件:**
- 修改: `src/services/system_config_service.py:49-92`

**Step 1: 添加脱敏逻辑**

定位到 `get_config()` 方法中构建 `item` 的循环（约第 65-77 行），修改为：

```python
for key in all_keys:
    raw_value = config_map.get(key, "")
    field_schema = schema_by_key[key]

    # 敏感字段脱敏：返回掩码值
    if field_schema.get("is_sensitive"):
        display_value = mask_token
    else:
        display_value = raw_value

    item: Dict[str, Any] = {
        "key": key,
        "value": display_value,  # 使用脱敏后的值
        "raw_value_exists": bool(raw_value),
        "is_masked": field_schema.get("is_sensitive", False),  # 标记是否被掩码
    }
    if include_schema:
        item["schema"] = field_schema
    items.append(item)
```

**Step 2: 验证修改**

确认以下逻辑正确：
- `is_sensitive=true` 时 `value` 为 `mask_token` (******)
- `is_sensitive=false` 时 `value` 为原始值
- 新增 `is_masked` 字段告知前端该值已被掩码

---

### Task 3: 编写单元测试

**文件:**
- 创建: `tests/test_system_config_masking.py`

**Step 1: 创建测试文件**

```python
# -*- coding: utf-8 -*-
"""测试敏感配置脱敏功能"""

import pytest
from src.services.system_config_service import SystemConfigService
from src.services.config_manager import ConfigManager


def test_sensitive_fields_are_masked():
    """测试标记为 is_sensitive 的字段被脱敏"""
    manager = ConfigManager.get_instance()
    service = SystemConfigService(manager)

    result = service.get_config(include_schema=True)

    # 检查敏感字段
    for item in result["items"]:
        schema = item.get("schema", {})
        if schema.get("is_sensitive"):
            # 敏感字段值应该是掩码
            assert item["value"] == "******"
            assert item["is_masked"] is True
        else:
            # 非敏感字段保留原值
            assert item["is_masked"] is False


def test_non_sensitive_fields_keep_value():
    """测试非敏感字段保持原值"""
    manager = ConfigManager.get_instance()
    service = SystemConfigService(manager)

    result = service.get_config(include_schema=True)

    # 找到非敏感字段（如 STOCK_LIST）
    stock_list = next((i for i in result["items"] if i["key"] == "STOCK_LIST"), None)
    if stock_list:
        # 非敏感字段不应是掩码
        assert stock_list["value"] != "******"
        assert stock_list["is_masked"] is False


def test_mask_token_customizable():
    """测试自定义掩码值"""
    manager = ConfigManager.get_instance()
    service = SystemConfigService(manager)

    custom_mask = "[HIDDEN]"
    result = service.get_config(include_schema=True, mask_token=custom_mask)

    # 检查敏感字段使用自定义掩码
    for item in result["items"]:
        if item.get("schema", {}).get("is_sensitive"):
            assert item["value"] == custom_mask
```

**Step 2: 运行测试确认通过**

```bash
cd /root/liyifan/daily_stock_analysis
pytest tests/test_system_config_masking.py -v
```

预期：所有测试通过

---

### Task 4: 手动测试 API 响应

**Step 1: 启动服务**

```bash
cd /root/liyifan/daily_stock_analysis
python3 main.py --serve-only --port 8001
```

**Step 2: 测试 API**

```bash
# 获取系统配置
curl -s http://localhost:8001/api/v1/system/config | jq '.items[] | select(.schema.is_sensitive == true) | {key, value, is_masked}'
```

预期输出示例：
```json
{
  "key": "TAVILY_API_KEYS",
  "value": "******",
  "is_masked": true
}
```

**Step 3: 测试非敏感字段**

```bash
curl -s http://localhost:8001/api/v1/system/config | jq '.items[] | select(.key == "STOCK_LIST") | {key, value, is_masked}'
```

预期输出示例：
```json
{
  "key": "STOCK_LIST",
  "value": "002594,561560,...",
  "is_masked": false
}
```

---

### Task 5: 测试前端配置页面

**Step 1: 打开前端配置页面**

访问: `http://localhost:8001/#/settings`

**Step 2: 验证敏感字段显示**

1. 找到敏感字段（如 Tavily API Keys）
2. 确认显示为 `******`
3. 点击眼睛图标
4. 确认仍然显示 `******`（后端已脱敏）
5. 确认显示"[敏感]"标签

**Step 3: 测试修改功能**

1. 修改敏感字段值为新值
2. 点击保存
3. 刷新页面
4. 确认新值已保存（仍显示为 `******`）

---

### Task 6: 更新 API 文档

**文件:**
- 修改: `api/v1/endpoints/system_config.py:37-39`

**Step 1: 更新 API 描述**

```python
summary="Get system configuration",
description="Read current configuration from .env. "
            "Sensitive fields (API keys, tokens) are masked for security.",
```

---

### Task 7: 提交代码

**Step 1: 提交实施代码**

```bash
git add src/services/system_config_service.py
git add tests/test_system_config_masking.py
git add api/v1/endpoints/system_config.py
git commit -m "feat(security): add backend masking for sensitive config fields

- API 返回敏感字段时自动脱敏为 ******
- 新增 is_masked 字段标识掩码状态
- 添加单元测试验证脱敏逻辑
- 更新 API 文档说明

修复前：API Key 明文返回存在泄露风险
修复后：敏感字段统一返回掩码值

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**Step 2: 合并到 feature 分支**

```bash
git status
```

---

## 验收标准

1. ✅ 所有 API Key 类字段返回 `******`
2. ✅ 非敏感字段返回原始值
3. ✅ 单元测试全部通过
4. ✅ 前端配置页面功能正常
5. ✅ 修改敏感值后保存生效
