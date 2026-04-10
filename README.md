# Daily Papers - AI精选论文

**自动抓取ArXiv论文，使用 Google Gemini 评分筛选高质量内容**

专为 **CV（计算机视觉）** 和 **LLM（大语言模型）** 研究者设计

## ✨ 特性

- **🆓 完全免费** - 使用 Google AI Studio 免费 API
- **🤖 自动运行** - GitHub Actions 每天自动运行
- **🎯 智能评分** - 四维度评估（0-100分）
- **💡 AI摘要** - 自动生成论文核心贡献摘要

## 🚀 快速开始

1. **Fork 本仓库**
2. **配置 API Key** - 添加 `GOOGLE_AI_API_KEY` 到 GitHub Secrets（[获取地址](https://aistudio.google.com/apikey)）
3. **启用 Actions** - Actions → Daily Papers → Enable workflow
4. **订阅通知** - Watch → All Activity

完成！系统每天 UTC 0:00（北京时间 8:00）自动运行。

📖 **详细设置请查看 [SETUP.md](SETUP.md)**

---

<!-- 论文将插入到这里 -->
<!-- PAPERS_START -->

## 📝 配置说明

### 研究领域

```yaml
keywords:
  - "Computer Vision"
  - "Object Detection"
  - "Diffusion Models"
  - "Large Language Models"
  - "Vision Language Models"
  - "Multimodal"
  - "Image Generation"
  - "Video Generation"
```

### 评分标准

```yaml
llm:
  min_score: 70                  # 最低评分（0-100）
  max_papers_per_keyword: 5      # 每个关键词保留论文数
  google:
    model: "auto"                # 自动选择最佳模型
```

## 📊 评分维度

每项 0-25 分，总分 0-100 分：

1. **创新性** - 是否提出新方法/新视角
2. **实用性** - 是否有实际应用价值
3. **严谨性** - 方法是否合理，实验是否充分
4. **清晰度** - 写作是否清晰易懂

## 📬 输出

- **README.md** - 每天更新当天精选论文
- **papers/** - 每天一个单独的 markdown 文件，记录历史论文

## 📁 项目结构

```bash
daily-papers/
├── .github/workflows/daily-papers.yml
├── config.yaml
├── main.py
├── README.md
├── papers/          # 历史论文（每天一个文件）
│   ├── 2026-04-10.md
│   └── ...
└── src/
    ├── api.py
    ├── llm_scorer.py
    ├── models.py
    ├── config.py
    └── logger.py
```

## 🛠️ 本地开发

```bash
pip install -r requirements.txt
export GOOGLE_AI_API_KEY="your-api-key"
python main.py
```

## License

MIT
