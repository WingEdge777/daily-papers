# Daily Papers - AI精选论文

**自动抓取ArXiv论文，使用 Google Gemini 评分筛选高质量内容**

专为 **CV（计算机视觉）** 和 **LLM（大语言模型）** 研究者设计

## ✨ 特性

- **🆓 完全免费** - 使用 Google AI Studio 免费 API（每天 1500 次请求）
- **🤖 自动运行** - GitHub Actions 每天自动运行，无需手动操作
- **📧 自动通知** - 创建 Issue 自动通知订阅者
- **🎯 智能评分** - 四维度评估：创新性、实用性、严谨性、清晰度
- **💡 AI摘要** - 自动生成论文核心贡献摘要

## 🚀 快速开始

### 1. Fork 本仓库

### 2. 获取 Google AI API Key

1. 访问 https://aistudio.google.com/apikey
2. 点击 **Create API Key**
3. 复制生成的 API Key

### 3. 配置 GitHub Secrets

进入你的仓库 → Settings → Secrets and variables → Actions → New repository secret

添加：

| Secret 名称 | 说明 | 获取地址 |
|------------|------|---------|
| `GOOGLE_AI_API_KEY` | Google AI Studio API密钥 | https://aistudio.google.com/apikey |

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

使用 Google AI Studio 免费 API：
- **Gemini 2.0 Flash** - 每天 1500 次免费请求
- **Gemini 1.5 Flash** - 每天 1500 次免费请求

**每日运行成本：$0** ✅

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
  max_papers_per_keyword: 5  # 每个关键词保留论文数
  
  google:
    model: "gemini-2.0-flash"  # 可选: gemini-1.5-flash, gemini-1.5-pro
```

## 🔄 工作流程

```
GitHub Actions 定时触发（每天）
    ↓
拉取 ArXiv 最新论文
    ↓
Google Gemini 评分（创新性、实用性、严谨性、清晰度）
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
  google:
    model: "gemini-1.5-pro"  # 更强大的模型
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
export GOOGLE_AI_API_KEY="your-api-key"

# 运行
python main.py
```

## 📖 相关文档

- [SETUP.md](SETUP.md) - GitHub Actions 详细设置指南

## License

MIT
