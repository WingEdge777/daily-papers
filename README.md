# Daily Papers - AI精选论文

**自动抓取ArXiv论文，使用LLM评分筛选高质量内容**

专为 **CV（计算机视觉）** 和 **LLM（大语言模型）** 研究者设计

## ✨ 特性

- **🆓 完全免费** - 自动选择 OpenRouter 最热门的免费模型
- **🤖 自动运行** - GitHub Actions 每天自动运行，无需手动操作
- **📧 自动通知** - 创建 Issue 自动通知订阅者
- **🎯 智能评分** - 四维度评估：创新性、实用性、严谨性、清晰度
- **💡 AI摘要** - 自动生成论文核心贡献摘要

## 🚀 快速开始

### 1. Fork 本仓库

### 2. 配置 API 密钥

进入你的仓库 → Settings → Secrets and variables → Actions → New repository secret

添加：

| Secret 名称 | 说明 | 获取地址 |
|------------|------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API密钥 | https://openrouter.ai/keys |

### 3. 启用 GitHub Actions

1. 进入 **Actions** 标签页
2. 点击 **I understand my workflows, go ahead and enable them**
3. 选择 **Daily Papers** → **Enable workflow**

### 4. 订阅通知

点击仓库右上角 **Watch** → **All Activity**

**完成！** 系统将每天 UTC 0:00（北京时间 8:00）自动运行，并通过邮件发送最新论文。

详细设置请查看 [SETUP.md](SETUP.md)

## 💰 成本说明

**完全免费！**

系统会自动从 OpenRouter 选择最热门的免费模型：

| 模型 | 价格 | 特点 |
|------|------|------|
| NVIDIA Nemotron 3 Super | **$0** | 使用量最高(563B tokens)，262K上下文 |
| Google Gemma 4 31B | **$0** | 最新(2026.4.3)，262K上下文 |
| Meta Llama 3.3 70B | **$0** | Meta官方，稳定可靠 |
| Qwen3 Next 80B | **$0** | Qwen3最新版本 |

**每日运行成本：$0** ✅

**自动模型选择：**
- 每次运行时自动获取 OpenRouter 免费模型列表
- 按使用量排序，选择最热门的模型
- 无需手动配置，始终保持最优选择

## 📝 配置说明

### 研究领域

默认关注 CV 和 LLM 领域：

```yaml
keywords:
  # CV领域
  - "Computer Vision"
  - "Object Detection"
  - "Diffusion Models"
  
  # LLM领域
  - "Large Language Models"
  - "Vision Language Models"
  - "Multimodal"
```

### LLM 评分

```yaml
llm:
  min_score: 7.0             # 最低评分（1-10）
  max_papers_per_keyword: 10 # 每个关键词保留论文数
  
  openrouter:
    model: "auto"  # 自动选择最热门的免费模型
    # 或指定模型：
    # model: "nvidia/nemotron-3-super"
```

## 🔄 工作流程

```
GitHub Actions 定时触发（每天）
    ↓
获取 OpenRouter 最热门免费模型
    ↓
拉取 ArXiv 最新论文
    ↓
LLM 评分（创新性、实用性、严谨性、清晰度）
    ↓
过滤低分论文（score < 7.0）
    ↓
创建 Issue + 更新 README
    ↓
GitHub 自动通知订阅者
```

## 📊 评分标准

LLM 从四个维度评分（1-10分）：

1. **创新性** - 是否提出新方法/新视角
2. **实用性** - 是否有实际应用价值
3. **严谨性** - 方法是否合理，实验是否充分
4. **清晰度** - 写作是否清晰易懂

## 📬 输出示例

每天会创建一个 Issue：

```markdown
## Computer Vision

| 标题 | 评分 | AI摘要 | 日期 |
|------|------|--------|------|
| **[YOLOv10](link)** | ⭐ 8.8/10 | 提出无NMS的实时目标检测 | 2024-01-15 |

## Large Language Models

| 标题 | 评分 | AI摘要 | 日期 |
|------|------|--------|------|
| **[GPT-4V](link)** | ⭐ 9.5/10 | 多模态理解的突破 | 2024-01-15 |
```

## 🔧 自定义

### 修改研究领域

编辑 `config.yaml`：

```yaml
keywords:
  - "Your Research Topic"
```

### 指定模型

编辑 `config.yaml`：

```yaml
llm:
  openrouter:
    model: "google/gemma-4-31b"  # 指定模型
```

### 修改运行时间

编辑 `.github/workflows/daily-papers.yml`：

```yaml
schedule:
  - cron: '0 1 * * *'  # UTC 1:00 = 北京时间 9:00
```

## 📁 项目结构

```
daily-papers/
├── .github/workflows/
│   └── daily-papers.yml    # GitHub Actions 配置
├── config.yaml              # 主配置文件
├── main.py                  # 主程序
├── src/
│   ├── api.py              # ArXiv API 客户端
│   ├── llm_scorer.py       # LLM 评分器
│   ├── model_selector.py   # 自动选择免费模型
│   ├── models.py           # 数据模型
│   ├── config.py           # 配置加载
│   └── logger.py           # 日志系统
└── tests/                  # 测试
```

## 🛠️ 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API 密钥
export OPENROUTER_API_KEY="sk-or-xxxxx"

# 运行
python main.py

# 测试
pytest tests/ -v
```

## 📖 相关文档

- [SETUP.md](SETUP.md) - GitHub Actions 详细设置指南

## License

MIT
