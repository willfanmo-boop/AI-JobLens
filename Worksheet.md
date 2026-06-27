# AI Job Platform — 完整开发 Roadmap

## Context（背景）

这个项目的目标是从一个单人原型，演变成一个真正可以公开给多用户使用的 AI 求职平台。每个用户可以上传自己的简历，平台根据个人背景做个性化的职位推荐和职业咨询。

当前代码已经有一个功能完整的后端（FastAPI + MySQL + Chroma + LangGraph Agent），但存在几个根本性的架构缺陷，阻止了多用户化：in-memory session、hardcoded resume 路径、全局单一的 Chroma collection。Frontend 目录完全为空。

**核心原则：每个 Phase 结束时，项目必须是完整可用的状态，不能有"半完成"的功能。**

---

## Phase 0 — 现状（已完成）

### 已有能力
- `POST /jobs/fetch` → jobspy 抓取 → MySQL → Chroma reindex
- `GET /jobs` → 分页返回职位列表
- `POST /chat` / `GET /chat/{id}/history` → LangGraph ReAct Agent 对话
- Agent 有 3 个工具：resume_retriever、chroma_job_retriever、pandas_job_retriever

### 已知 Bug / 缺陷（按优先级排序）

| # | 状态 | 问题 | 文件 | 影响 |
|---|------|------|------|------|
| 1 | ❌ 未修复 | Session 存在内存 dict 里，重启丢失 | `api/routes/chat.py:11` | 重启后聊天记录消失 |
| 2 | ❌ 未修复 | Resume 路径 hardcoded 为 `docs/FanMo_Resume.md` | `core/rag/resume_indexer.py:13` | 无法上传新简历 |
| 3 | ❌ 未修复 | 单一全局 Chroma "resume" collection | `core/agent.py:24-34` | 多用户时会混用简历 |
| 4 | ✅ 已完成 | Frontend 目录为空 | `frontend/` | 没有 UI |
| 5 | ❌ 未修复 | Chroma 每次全量重建（DELETE + 全量 embed） | `core/rag/job_indexer.py:53-65` | 慢、费 token |
| 6 | ❌ 未修复 | `allow_origins=["*"]` | `main.py:35` | 安全风险 |
| 7 | ❌ 未修复 | OpenAI API Key 存在 `.env`，注意不要 commit | `.env` | 安全风险 |

### 补充说明：前端 localStorage

`frontend/chat.html` 使用 `localStorage` 存储聊天历史（见 `chat.html:206`），这是**客户端持久化**。
这意味着：刷新页面历史不消失（localStorage 行为）。但如果后端重启，`session_id` 对应的服务端消息历史会丢失——两者不同步。
1B 完成后，前端的 `session_id` 与后端 DB 对应，两侧数据才真正一致。

---

## Phase 1 — 单人版本完整可用

**目标：你自己可以打开浏览器，上传简历，聊天，浏览职位，重启后数据不丢失。不碰多用户。**

**整体进度：25%（1A 完成，1B/1C/1D 待做）**

**本阶段不需要考虑：** 用户注册/登录、多用户隔离、部署、Docker、限流、增量索引

---

### ✅ 1A. Frontend 构建（已完成）

三个页面已全部构建完成，使用纯 HTML + Vanilla JS + `support.js` 组件库：

| 文件 | 状态 | 备注 |
|------|------|------|
| `frontend/chat.html` | ✅ 完成 | 多会话侧边栏，localStorage 持久化，Markdown 渲染 |
| `frontend/jobs.html` | ✅ 完成 | 职位卡片列表，分页，Fetch New Jobs 表单 |
| `frontend/resume.html` | ✅ 完成 | 文件上传 UI（调用 `POST /resume/upload`，后端接口待做） |
| `frontend/support.js` | ✅ 完成 | 共享组件库 |

**注意事项：**
- `resume.html` 的上传按钮会调用 `POST /resume/upload`，此接口目前不存在，需要 1C 完成后才能真正使用
- 前端聊天历史存在 `localStorage`，刷新不丢；后端 session 目前存在内存，重启丢失（1B 修复）

---

### 🔜 下一步：1B + 1C 并行开工（推荐顺序）

**建议先做 1B，再做 1C，最后做 1D。原因：**
- 1B 修复的是核心体验问题（重启丢历史），改动集中在后端 3 个文件
- 1C 依赖 1B 中新建的 DB 基础设施（改 `db/models.py` 和 `db/crud.py`）
- 1D 是纯 API 增强，独立性强，最后做

---

### ❌ 1B. Chat Session 持久化（修复 Bug #1）— 当前首要任务

**修改 `db/models.py`** — 新增 ChatSession 表：
```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id           = Column(String(36), primary_key=True)  # uuid4
    messages_json = Column(Text(4294967295))              # LONGTEXT, JSON 序列化
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**修改 `db/crud.py`** — 新增两个函数：
- `get_session_messages(session_id: str) -> list[dict]` — 从 DB 读取并 JSON 反序列化
- `save_session_messages(session_id: str, messages: list[dict])` — JSON 序列化写入 DB

**修改 `api/routes/chat.py`** — 把 `sessions: dict[str, list] = {}` 替换为 DB 调用。LangChain 消息对象序列化格式：`[{"role": "human"/"ai", "content": "..."}]`。

**完成后验证：**
```bash
# 发一条消息，记录 session_id
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "hello"}'
# 重启 uvicorn（Ctrl+C 再启动）
# 再查历史，应该还在
curl http://localhost:8000/chat/{session_id}/history
```

---

### ❌ 1C. Resume 上传 API（修复 Bug #2）

**新建 `api/routes/resume.py`：**
```
POST /resume/upload
  - multipart/form-data 接收文件（.md 或 .pdf）
  - 保存到 docs/resume.{ext}
  - 调用 index_resume(file_path)
  - 返回 {"message": "...", "chunks": N}
```

**修改 `core/rag/resume_indexer.py`：**
- `index_resume()` 改为接受可选参数 `file_path: str = None, collection_name: str = "resume"`
- 如果 `file_path` 是 `.pdf`，用 `langchain_community.document_loaders.PyPDFLoader` 解析，再用 `RecursiveCharacterTextSplitter` 分块
- 如果是 `.md`，保留现有 `MarkdownHeaderTextSplitter` 逻辑

**修改 `requirements.txt`** — 新增：
```
python-multipart>=0.0.9
pypdf>=4.0.0
langchain-community>=0.3.0
```

**修改 `main.py`** — 注册 resume router：
```python
from api.routes.resume import router as resume_router
app.include_router(resume_router)
```

**完成后验证：**
```bash
curl -X POST http://localhost:8000/resume/upload -F "file=@docs/FanMo_Resume.md"
# 返回 {"message": "...", "chunks": N}
# 打开 frontend/resume.html，拖拽上传文件，看到成功提示
```

---

### ❌ 1D. 职位搜索过滤（完善 GET /jobs）

**修改 `api/routes/jobs.py`** — 给 `GET /jobs` 添加 query params：
- `search: Optional[str]` — 按 title/company LIKE 模糊匹配
- `is_remote: Optional[bool]`
- `job_type: Optional[str]`

**修改 `db/crud.py`** — `list_jobs()` 接受并应用这些过滤条件，用 SQLAlchemy `where()` 实现。

**完成后验证：**
```bash
# 测试搜索过滤
curl "http://localhost:8000/jobs?search=python&is_remote=true"
# 前端 jobs.html 的搜索框和 Remote 切换能正确过滤
```

---

### Phase 1 完成标志 ✅

- [x] 打开 `http://localhost:8000` 看到聊天界面
- [ ] 访问 `/resume.html`，上传 `.md` 或 `.pdf` 简历，看到成功提示（需 1C）
- [ ] 聊天时 AI 能引用简历内容（需 1C）
- [ ] **重启服务器后**，聊天记录依然存在（需 1B）
- [x] 访问 `/jobs.html`，看到职位列表
- [x] "Fetch New Jobs" 按钮触发抓取，新职位出现在列表
- [ ] 职位列表支持关键词搜索 + Remote 过滤（需 1D）

---

## Phase 2 — 多用户基础

**目标：任何人可以注册账号，上传自己的简历，得到个性化推荐，数据完全隔离。**

**预计时间：5-8 天**

**本阶段不需要考虑：** 邮件验证、找回密码、OAuth/社交登录、Redis、Docker、水平扩展

---

### 2A. 用户数据库模型

**修改 `db/models.py`** — 新增两张表：

```python
class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    email         = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

class UserResume(Base):
    __tablename__ = "user_resumes"
    id                 = Column(Integer, primary_key=True)
    user_id            = Column(Integer, ForeignKey("users.id"), unique=True)
    file_path          = Column(String(500))           # "uploads/42/resume.pdf"
    chroma_collection  = Column(String(100))           # "resume_user_42"
    indexed_at         = Column(DateTime)
```

同时给 ChatSession 加 `user_id` 外键：
```python
user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
```

> **注意**：Jobs 表不需要加 user_id，职位库是全局共享的，只有简历和聊天记录是每人独立的。

> **注意**：这是第一次需要 ALTER 已存在的表（给 chat_sessions 加列）。需要手动在 MySQL 执行 `ALTER TABLE chat_sessions ADD COLUMN user_id INT;`，或者引入 Alembic（推荐在 Phase 3 再加）。

---

### 2B. JWT 认证系统

**修改 `requirements.txt`** — 新增：
```
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

**新建 `core/auth.py`：**
```python
def hash_password(plain: str) -> str          # bcrypt
def verify_password(plain: str, hashed: str) -> bool
def create_access_token(user_id: int) -> str  # JWT，24小时过期
def decode_token(token: str) -> int            # 返回 user_id，否则抛 401
```
JWT_SECRET 从 `os.getenv("JWT_SECRET")` 读取，加进 `.env`。

**新建 `api/routes/auth.py`：**
```
POST /auth/register  → {email, password} → 创建用户 → {"message": "registered"}
POST /auth/login     → {email, password} → 验证 → {"access_token": "...", "token_type": "bearer"}
```

**新建 `api/deps.py`：**
```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> int:
    return decode_token(token)  # 返回 user_id
```
这个 Dependency 注入到需要认证的 endpoint，自动读取 `Authorization: Bearer <token>` header。

**修改 `main.py`** — 注册 auth router。

---

### 2C. 每用户独立简历隔离（修复 Bug #3）

**策略：** Chroma collection 按 user_id 命名：`resume_user_42`。

**修改 `api/routes/resume.py`：**
- 注入 `user_id: int = Depends(get_current_user)`
- 文件保存到 `uploads/{user_id}/resume.{ext}`（需创建目录）
- 调用 `index_resume(file_path, collection_name=f"resume_user_{user_id}")`
- 在 `user_resumes` 表写入记录

---

### 2D. Agent 改为工厂函数（核心架构改动）

当前 `core/agent.py` 是模块级单例，`resume_vectorstore` 是全局的。这是多用户化最关键的改动。

**修改 `core/agent.py`** — 从单例改为工厂函数：
```python
def build_agent(resume_collection_name: str):
    resume_vectorstore = Chroma(
        collection_name=resume_collection_name,  # 每次传入当前用户的 collection
        embedding_function=embedding,
        persist_directory=VECTOR_DB_PATH,
    )
    # 在这里定义 close over 这个 vectorstore 的 tools
    # 返回 create_react_agent(...)
```

**修改 `api/routes/chat.py`：**
- 注入 `user_id: int = Depends(get_current_user)`
- 从 DB 查该用户的 `chroma_collection` 名称
- 调用 `build_agent(collection_name)` 再 invoke（如果用户还没上传简历则返回 400）
- Session 查询/保存加 `user_id` 过滤

> **性能说明：** `build_agent()` 每次请求都创建新的 Chroma handle，这是字典查找（Chroma 懒加载），不是重新 embed。低流量下完全够用。如果感觉慢可以用 `dict` 缓存 `{user_id: agent_instance}`。

---

### 2E. Frontend 认证

**新建 `frontend/login.html`：**
- 登录/注册两个表单
- 成功后把 JWT 存到 `localStorage`
- 封装 JS 工具函数 `getAuthHeaders()` 返回 `{"Authorization": "Bearer " + token}`

**修改 `frontend/index.html`、`jobs.html`、`resume.html`：**
- 所有 `fetch()` 调用加上 auth headers
- 没有 token 时自动跳转到 `/login.html`

**公开 vs 需要认证的路由：**
- `GET /jobs` — 保持公开（不需要登录可浏览职位）
- `POST /chat`、`POST /resume/upload` — 必须认证

---

### Phase 2 完成标志 ✅

- [ ] 注册两个不同账号
- [ ] 各自上传不同简历
- [ ] 用户 A 的聊天只引用用户 A 的简历，用户 B 同理
- [ ] 聊天记录重启后不丢失，且两用户隔离
- [ ] 不带 token 调用 `/chat` 返回 401
- [ ] 未登录用户依然可以浏览职位

---

## Phase 3 — 生产可用

**目标：部署到公网，自动抓取职位，安全加固，多用户稳定运行。**

**预计时间：5-10 天**

**本阶段不需要考虑：** 微服务、Kubernetes、CDN、A/B 测试、高级分析

---

### 3A. 自动定时抓取职位

当前每次都要手动 `POST /jobs/fetch`，这是日常使用的最大摩擦点。

**修改 `requirements.txt`** — 新增：`apscheduler>=3.10.0`

**新建 `core/scheduler.py`：**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.job_fetcher import fetch_and_store_jobs

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        fetch_and_store_jobs,
        "cron",
        hour=6,  # 每天早上 6 点
        kwargs={"search_term": "software engineer", "location": "Canada", "results_wanted": 100}
    )
    scheduler.start()
```

**修改 `main.py`** — 在 `lifespan` 的 startup 部分调用 `start_scheduler()`（必须在 async context 内，不能在模块顶层）。

---

### 3B. Chroma 增量索引（修复 Bug #5）

当前 `core/rag/job_indexer.py` 每次全量 DELETE + 全量 embed，1000 条职位需要 30+ 秒和大量 OpenAI token。

**修改 `core/rag/job_indexer.py`：**
```python
def index_jobs() -> int:
    # 1. 获取 Chroma 中已有的 doc IDs
    existing_ids = set(existing_store.get(include=[])["ids"])
    
    # 2. 从 MySQL 取出所有职位 ID
    # 3. 计算差集：只 embed 新增的职位
    new_jobs = [j for j in all_jobs if str(j["id"]) not in existing_ids]
    
    # 4. 只 add 新增部分，不 delete_collection
    store.add_documents(new_documents)
```
用 MySQL 的 `id`（整数）作为 Chroma 的 document ID（字符串化）。

---

### 3C. 安全加固

**修改 `main.py`** — 收窄 CORS：
```python
allow_origins=["https://yourdomain.com", "http://localhost:8000"]
```

**修改 `requirements.txt`** — 新增：`slowapi>=0.1.9`

对 `/chat` endpoint 加限流：30 次/分钟/IP；对 `/jobs/fetch` 加限流：5 次/小时/用户。

**修改 `core/auth.py`** — JWT secret 改为从 `os.getenv("JWT_SECRET")` 读取，不 hardcode。

---

### 3D. 引入 Alembic 数据库迁移

Phase 2 开始需要修改已存在的表结构，这时候 SQLAlchemy 的 `create_all` 不够用了。

**修改 `requirements.txt`** — 新增：`alembic>=1.13.0`

初始化 Alembic，为每次 schema 变更生成 migration 文件，替代手动 ALTER TABLE。

---

### 3E. Docker 化部署

**新建 `Dockerfile`：**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**新建 `docker-compose.yml`：**
```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./uploads:/app/uploads
      - ./vector_db:/app/vector_db
    depends_on: [db]
  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: jobplatform
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
volumes:
  mysql_data:
```

`uploads/` 和 `vector_db/` 挂载为 volume，容器重启不丢数据。

**新建 `.env.example`** — 不含真实 key 的模板文件，提交到 git：
```
OPENAI_API_KEY=sk-your-key-here
MYSQL_URL=mysql+asyncmy://root:password@db/jobplatform
JWT_SECRET=your-secret-here
MYSQL_ROOT_PASSWORD=your-db-password-here
```

---

### 3F. 云部署

推荐 **Railway.app** 或 **Render.com**（支持 Dockerfile + managed MySQL，一条命令部署，月费 ~$10-20）。避免在此阶段用 AWS/GCP，IAM/VPC 配置会消耗大量时间。

> **⚠️ 安全提醒：** `.env` 里的 OpenAI API Key 不要 commit 到 git。在 Railway/Render 的环境变量 UI 里配置，不要上传 `.env` 文件。

---

### Phase 3 完成标志 ✅

- [ ] `git push` → 自动部署到云端
- [ ] 每天早上 6 点自动抓取新职位，无需手动触发
- [ ] 新职位增量 embed（不重建整个 collection）
- [ ] `/chat` 超过限流返回 429
- [ ] CORS 只允许你的域名
- [ ] 服务器重启后所有数据完好

---

## Phase 4 — 扩展与优化（可选，Phase 1-3 稳定后再考虑）

| 功能 | 实现方式 | 工作量 |
|------|---------|--------|
| 更多职位来源 | `job_fetcher.py` 的 `site_names` 加入 `glassdoor`、`zip_recruiter` | 0.5天 |
| 职位匹配评分 | `POST /jobs/match`：用用户简历向量在 job collection 做相似度搜索，返回 cosine score | 1-2天 |
| 职位收藏 | 新增 `UserSavedJob` 表，`POST /jobs/{id}/save`，前端加书签图标 | 1-2天 |
| 数据看板 | `frontend/dashboard.html`，Chart.js（CDN 引入），展示职位来源分布、薪资分布、每日新增趋势 | 2-3天 |
| 移动端适配 | 纯 CSS flexbox/grid，不需要单独 build，测试部署 URL 即可 | 0.5天 |

---

## 架构决策总结

### Chroma Collection 命名规范
- `"job"` — 全局共享，所有用户看同一份职位库
- `"resume_user_{id}"` — 每用户独立，如 `"resume_user_42"`

### 不需要 Redis（Phase 1-3）
MySQL 的 `chat_sessions` 表（JSON 列）足以支撑数百用户的 session 持久化。Redis 只在数千并发连接时才有必要。

### Frontend 技术选择
Frontend 完全从零新建，有两条路可以走：

- **纯 HTML + Vanilla JS**：零配置，FastAPI StaticFiles 直接托管，适合快速上线验证功能。缺点是功能复杂后代码难以维护。
- **React + Vite**：组件化清晰，状态管理干净，长期可维护性更好。需要单独的 `npm run build` 步骤，产物输出到 `frontend/dist/` 再由 FastAPI 托管。

建议在开始 Phase 1 前先决定这个问题，因为它决定了所有前端文件的组织方式。功能简单选前者，打算长期迭代选后者。

### 数据库迁移策略
- Phase 1-2 早期：`Base.metadata.create_all` 处理新表创建（idempotent）
- Phase 2 首次需要 ALTER 已存在表时：引入 **Alembic**
- Phase 3 生产部署：所有 schema 变更必须走 Alembic migration

---

## 每个 Phase 改动的文件一览

### Phase 1 — 新建
- `frontend/index.html`（聊天主页，全新构建）
- `frontend/jobs.html`（职位浏览页，全新构建）
- `frontend/resume.html`（简历上传页，全新构建）
- `api/routes/resume.py`

### Phase 1 — 修改
- `main.py` — 加 StaticFiles + resume router（StaticFiles 必须最后挂载）
- `db/models.py` — 加 ChatSession 模型
- `db/crud.py` — 加 session CRUD 函数
- `api/routes/chat.py` — 替换 in-memory dict 为 DB
- `api/routes/jobs.py` — 加搜索过滤参数
- `core/rag/resume_indexer.py` — 参数化 file_path 和 collection_name
- `requirements.txt` — 加 python-multipart、pypdf、langchain-community

### Phase 2 — 新建
- `core/auth.py`
- `api/routes/auth.py`
- `api/deps.py`
- `frontend/login.html`
- `uploads/{user_id}/` 目录（运行时创建）

### Phase 2 — 修改
- `db/models.py` — 加 User、UserResume，ChatSession 加 user_id
- `core/agent.py` — 从模块级单例改为 `build_agent(collection_name)` 工厂函数
- `api/routes/chat.py` — 注入 user_id，调用 build_agent
- `api/routes/resume.py` — 按 user_id 存文件和 collection
- `frontend/*.html` — 所有 fetch 加 auth headers

### Phase 3 — 新建
- `core/scheduler.py`
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`

### Phase 3 — 修改
- `core/rag/job_indexer.py` — 改为增量索引
- `main.py` — 收窄 CORS，注册 scheduler，加限流
- `requirements.txt` — 加 apscheduler、slowapi、alembic

---

## 验证方式

### Phase 1 验证
```bash
# 启动服务
uvicorn main:app --reload

# 验证 session 持久化
curl -X POST http://localhost:8000/chat -d '{"message": "hello"}' # 得到 session_id
# 重启 uvicorn
curl http://localhost:8000/chat/{session_id}/history  # 历史应该还在

# 验证 resume 上传
curl -X POST http://localhost:8000/resume/upload -F "file=@docs/FanMo_Resume.md"

# 验证前端
open http://localhost:8000           # 聊天页
open http://localhost:8000/jobs.html # 职位列表
open http://localhost:8000/resume.html # 简历上传
```

### Phase 2 验证
```bash
# 注册两个账号
curl -X POST http://localhost:8000/auth/register -d '{"email":"a@test.com","password":"pass1"}'
curl -X POST http://localhost:8000/auth/register -d '{"email":"b@test.com","password":"pass2"}'

# 各自登录、上传不同简历、各自聊天
# 验证 A 的聊天结果只引用 A 的简历

# 验证未认证请求
curl -X POST http://localhost:8000/chat -d '{"message":"hi"}'  # 应返回 401
```

### Phase 3 验证
```bash
docker-compose up --build  # 应该成功启动
# 等到每天 6 AM，检查日志确认自动抓取运行
# 检查 /jobs 返回的 total 数量有增加
```
