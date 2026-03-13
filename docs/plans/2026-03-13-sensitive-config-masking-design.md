# 敏感配置后端脱敏设计

## 概述

对系统配置 API 中的敏感字段（API Key、Token 等）进行后端脱敏处理，防止明文返回。

## 问题

当前 GET /api/v1/system/config 返回完整的 API key 明文，存在安全风险。

## 解决方案

### 方案选择

采用 **Schema 标记脱敏** 方案：
- 复用现有的 `is_sensitive` schema 标记
- 服务端统一返回掩码值 `******`
- 前端显示逻辑不变（已默认隐藏）

### 实现细节

**修改文件：** `src/services/system_config_service.py`

**核心改动：**
```python
def get_config(self, include_schema: bool = True, mask_token: str = "******") -> Dict[str, Any]:
    for key in all_keys:
        field_schema = schema_by_key[key]
        raw_value = config_map.get(key, "")

        # 新增：敏感字段脱敏
        if field_schema.get("is_sensitive"):
            raw_value = mask_token

        item = {
            "key": key,
            "value": raw_value,
            # ...
        }
```

**受影响的字段（示例）：**
- `TAVILY_API_KEYS`
- `SERPAPI_API_KEYS`
- `GEMINI_API_KEY`
- `LITELLM_API_KEY`
- 其他标记为 `is_sensitive=True` 的字段

### 兼容性

- **修改操作**：不受影响，通过 `mask_token` 保留原值
- **前端显示**：不受影响，仍可点击眼睛图标（但只显示掩码）
- **配置更新**：不受影响，用户输入新值会覆盖

## 实施步骤

1. 修改 `SystemConfigService.get_config()` 方法
2. 确认所有敏感字段已标记 `is_sensitive`
3. 测试 API 响应确认脱敏生效
4. 测试前端配置页面功能正常
