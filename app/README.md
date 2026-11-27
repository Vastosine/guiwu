# 物归 · 校园失物智能招领（原型）

一个从「拍照」到「交接」的完整闭环：多模态识别入库 → 口语检索与可解释匹配 → 特征问答核验 → 管理端核销。

> 零依赖：只用 Python 3.12 标准库 + 原生 JavaScript。**不需要 pip install，不需要 npm。**

---

## 启动

**Windows 下双击 `run.cmd` 即可**（它会自动找解释器：py 启动器 → 常见安装路径 → DSH 自带 Python）。

命令行方式：

```powershell
cd app
.\run.cmd
```

也可以直接用任意 Python 3.8+ 启动：

```powershell
python server.py
```

浏览器打开 <http://127.0.0.1:8000>（学生端）与 <http://127.0.0.1:8000/admin>（管理端）。

> **如果提示 `Python was not found`**：说明机器上的 `python` 只是 Microsoft Store 的占位别名，并没有真正安装。
> 装一个即可（约两分钟，装完重开终端）：
>
> ```powershell
> winget install -e --id Python.Python.3.12
> ```
>
> 不装也能跑——`run.cmd` 会自动回退到 DSH 自带的解释器，只是换一台电脑就没得用了。

| 环境变量 | 作用 |
|---|---|
| `PORT` | 端口，默认 8000 |
| `DASHSCOPE_API_KEY` | 配上就走真实模型；不配则走规则实现 |
| `QWEN_VL_MODEL` / `QWEN_TEXT_MODEL` | 模型名，默认 `qwen-vl-max` / `qwen-max` |

Windows 用法示例：

```powershell
$env:DASHSCOPE_API_KEY="sk-xxxx"
python server.py
```

---

## 两种模式

| | 规则模式（默认） | 模型模式 |
|---|---|---|
| 触发条件 | 未配置 API Key | 配置了 `DASHSCOPE_API_KEY` |
| 识别 | 返回示例字段，前端提示「已预填，请确认」 | 千问-VL 读图输出字段 |
| 改写 / 精排 / 出题 / 判分 | 规则与字符重合度 | Qwen-Max |
| 依赖网络 | 否 | 是 |

**关键设计：模型是增强，不是依赖。** 任何一次模型调用超时、限流或返回非法 JSON，都会自动降级到规则实现，并写一条 `llm_fallback` 日志——答辩现场断网，闭环依然跑得通。

---

## 目录

```
app/
├── server.py         HTTP 路由与接口（REST 风格，可平移至 FastAPI）
├── core.py           SQLite、种子数据、口语改写规则、硬过滤、规则打分
├── llm.py            模型网关 + 5 条提示词 + 规则兜底实现
├── smoke.py          端到端冒烟测试（16 项断言）
├── static/
│   ├── index.html    学生端：拾得入库 / 智能寻回 / 特征核验
│   ├── admin.html    管理端：核销 / 列表 / 日志
│   └── app.css       设计系统（与 PPT、文档同一套色板）
└── data.db           首次启动自动创建并播种 8 条演示数据
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 模式与物品数 |
| POST | `/api/parse` | 图片 → 结构化字段 |
| POST | `/api/items` | 发布入库 |
| POST | `/api/search` | 口语 → 条件 + Top-3 + 理由 |
| GET | `/api/items/{id}/questions` | 生成核验题（不返回答案要点） |
| POST | `/api/verify` | 判分、过阈值发码 |
| POST | `/api/redeem` | 核销认领码 |
| GET | `/api/items` · `/api/logs` | 列表 · 日志 |
| POST | `/api/reset` | 一键恢复 8 条演示数据 |

自测：

```bash
python smoke.py        # 需先启动 server.py
```

---

## 演示动线（对应视频脚本）

1. **拾得入库**：拍照 → 字段可编辑 → 打开隐私开关 → 发布
2. **智能寻回**：输入「昨天下午在3教丢了个白色无线耳机」→ 看 chip 与 Top-3 → 读理由
3. **特征核验**：申请认领 → 三道题（都围绕同一处细节）→ 通过 → 拿到 `A7K-92F`
4. **反例**：答「不知道 / 忘了 / 不清楚」→ 被拒并记录一次尝试
5. **管理端**：输入认领码 → 状态变更 → 日志多一条

> 演示前点一次管理端的「重置演示数据」，避免出现「该认领码已被使用」。

---

## 已知限制（答辩时被问就照实说）

1. **规则模式下没有真正的视觉能力**：`/api/parse` 返回示例字段，界面上会标注「已预填，请确认」。要看真实识别效果，配 Key。
2. **检索是「硬过滤 + 精排」两段式**，没有向量召回；数据量超过几百条时需要补 embedding。文档第 4 章已把它列为 V1.1。
3. **核验判分用字符重合度**近似语义等价，同义表达容忍度有限；换成真模型后走 `P_JUDGE`，效果明显更好。

## 下一步（如果有第四天）

- 接 `text-embedding-v4` 做向量召回，替换 `core.hard_filter` 里的关键词召回
- 把「认领码 24 小时过期」真正落成定时清理
- 管理端加导出（月度报告）
