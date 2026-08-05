# V3 Feature: [功能名称]

> 创建日期: YYYY-MM-DD | 作者: [name] | 状态: draft / review / approved

---

## 1. 动机

- 这个功能解决什么问题？
- 用户现在怎么做，有什么痛点？
- 为什么现在做？（竞品对比 / 用户反馈）

---

## 2. 方案对比

### 方案 A: [简述]

- 优点:
- 缺点:

### 方案 B: [简述]

- 优点:
- 缺点:

### 推荐方案: [方案X]

- 选择理由:

---

## 3. 接口设计

### API 端点

```
POST /api/xxx
GET  /api/xxx/{id}
PUT  /api/xxx/{id}
```

### 请求/响应模型

```python
class XXXRequest(BaseModel):
    field: str

class XXXResponse(BaseModel):
    id: str
    field: str
```

### 前端页面

- 路由: `/project/:id/xxx`
- 组件: `XXXPage.tsx`
- 使用的共享组件: DataTable, EmptyState

---

## 4. 数据模型变更

```python
class NewModel(Base):
    __tablename__ = "new_table"
    id = Column(String, primary_key=True)
    ...
```

- 是否需要 migration: 是/否
- 是否影响现有模型: 是/否

---

## 5. Agent / Skill 变更

- 新增 Skill: 名称 + 能力
- 修改 Prompt: 哪个模板，改什么
- 新增 Agent 节点: 名称 + 在 pipeline 中的位置

---

## 6. 测试计划

### 单元测试
- [ ] test_xxx 覆盖核心逻辑

### 集成测试
- [ ] API 端点 CRUD 测试

### 手动测试
- [ ] 场景1: ...
- [ ] 场景2: ...

---

## 7. 风险

- 性能风险:
- 安全风险:
- 兼容性: 是否 break 现有功能？

---

## 审批

- [ ] 设计评审通过
- [ ] 实现完成
- [ ] 测试通过
- [ ] 文档更新
