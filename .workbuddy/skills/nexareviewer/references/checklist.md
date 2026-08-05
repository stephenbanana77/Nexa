# Nexa Code Review Checklist

10 条生产级标准，按优先级排序。

---

### 1. Auth 认证

**检查规则**: 所有新增的 API 端点（@router.get/post/put/delete）必须包含 `current_user: User = Depends(get_current_user)`。

**通过条件**: 每个新路由函数签名中有 `get_current_user` 依赖。

**常见违规**:
```python
# ❌ 缺少认证
@router.get("/{id}")
def get_resource(id: str, db: Session = Depends(get_db)):
    ...

# ✅ 正确
@router.get("/{id}")
def get_resource(id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ...
```

---

### 2. Error 错误处理

**检查规则**: 所有 `try/except` 块必须有日志记录。SSE/流式端点必须在生成器内捕获异常并发送 error 事件。不允许 `except Exception: pass`。

**通过条件**: 每个异常捕获块中可见 `logger.exception()` 或 `logger.error()`。

**常见违规**:
```python
# ❌ 吞噬异常
except Exception:
    pass

# ✅ 正确
except Exception as e:
    logger.exception("Failed to process")
    raise HTTPException(status_code=500, detail=str(e))
```

---

### 3. Type 类型安全

**检查规则**: 新增的 TypeScript 代码中不允许出现 `any` 类型（除非是与第三方库交互的边界代码）。Python 函数参数应有类型注解。

**通过条件**: 新增代码中 `any` 出现次数 ≤ 1。

---

### 4. Pagination 分页

**检查规则**: 新增的列表端点必须支持 `skip` + `limit` 查询参数，返回 `{items, total, skip, limit}` 格式。不允许裸 `query.all()` 返回全部数据。

**通过条件**: 列表端点使用 `offset(skip).limit(limit)` 且有 `.count()` 获取总数。

**常见违规**:
```python
# ❌ 无分页
items = db.query(Model).all()
return items

# ✅ 正确
total = db.query(Model).count()
items = db.query(Model).offset(skip).limit(limit).all()
return {"items": items, "total": total, "skip": skip, "limit": limit}
```

---

### 5. Injection 注入防护

**检查规则**: 
- 用户输入进入 SQL 前必须经过 `_validate_sql()` 处理
- 用户输入进入 LLM prompt 前必须经过 `sanitize_user_input()` 处理
- 新增的数据库查询不允许使用字符串拼接构造 SQL

**通过条件**: 所有用户输入进入危险上下文前有清洗步骤。

---

### 6. Config 配置

**检查规则**: 
- 不允许硬编码的魔法数字（阈值、超时、限制值）
- 不允许硬编码的 URL（localhost、127.0.0.1）
- 配置项应从 `settings` 对象或环境变量读取

**通过条件**: 代码中无新增硬编码值。

**常见违规**:
```python
# ❌ 硬编码
temperature = 0.1
timeout = 30

# ✅ 正确
temperature = settings.LLM_TEMPERATURE
timeout = settings.LLM_TIMEOUT
```

---

### 7. Concurrency 并发安全

**检查规则**: 
- 共享的可变状态（dict、list、set）必须有锁保护
- `EngineRegistry.get()` 调用在加锁范围内
- 不在 async 函数中执行长时间阻塞的同步调用

**通过条件**: 新增的全局/类级别可变状态有锁保护。

---

### 8. Resource 资源清理

**检查规则**: 
- 文件句柄通过 `with` 或 `finally` 确保关闭
- 数据库 session 通过 `get_db()` 依赖注入管理
- 临时文件在 `finally` 中删除

**通过条件**: 无资源泄漏风险。

---

### 9. Health 可观测性

**检查规则**: 
- 新增的关键路径操作应有日志（`logger.info`）
- 新增的外部 API 调用（LLM、数据库、文件 IO）应有错误日志
- 健康检查端点无需修改（已有 `/api/health` 和 `/api/health/ready`）

---

### 10. API 设计

**检查规则**: 
- 请求体使用 Pydantic model，不裸用 dict
- 敏感字段使用 `SecretStr`（密码、token、API key）
- 响应格式一致（列表用 `{items, total}`，单对象用裸对象）
- 错误响应使用 `HTTPException` 带适当的状态码
- 路径参数优于查询参数用于资源标识
