# GitHub Actions 快速部署指南

## 当前状态

✅ **已完成：**
- 代码重构完成
- Google AI Studio 集成完成
- API Key 已验证有效

⚠️ **本地测试问题：**
- 免费模型临时限流（429）
- 代理连接不稳定
- 这些问题在 GitHub Actions 中通常不会出现

## 🚀 快速部署

### 1. 推送代码到 GitHub

```bash
# 添加所有更改
git add .

# 提交
git commit -m "feat: 使用 Google AI Studio 替代 OpenRouter"

# 推送
git push origin main
```

### 2. 配置 GitHub Secrets

进入你的 GitHub 仓库：
1. Settings → Secrets and variables → Actions
2. 点击 "New repository secret"
3. 添加：
   - Name: `GOOGLE_AI_API_KEY`
   - Value: `你的Google AI API Key`
4. 点击 "Add secret"

**获取 API Key：**
访问 https://aistudio.google.com/apikey 创建

### 3. 启用 GitHub Actions

1. 进入 Actions 标签页
2. 选择 "Daily Papers"
3. 点击 "Enable workflow"

### 4. 手动测试

1. Actions → Daily Papers
2. 点击 "Run workflow" → "Run workflow"
3. 等待运行完成（约 2-5 分钟）
4. 查看 Issues 标签页，检查是否创建了新 Issue

### 5. 查看日志

如果运行失败：
1. 点击失败的工作流
2. 查看详细日志
3. 检查错误信息

## 💡 为什么 GitHub Actions 更好？

1. **网络稳定** - GitHub 服务器网络质量高
2. **无代理问题** - 直连 Google AI API
3. **自动化** - 每天自动运行，无需手动操作

## 🔍 如果 GitHub Actions 也失败

检查日志中的错误：

### 如果是 429（限流）
```
解决方案：
1. 等待几分钟后重试
2. Google AI Studio 免费版每天 1500 次请求
```

### 如果是 401（认证失败）
```
解决方案：
1. 检查 Secret 名称是否正确（GOOGLE_AI_API_KEY）
2. 检查 API Key 是否有效
3. 重新生成 API Key
```

### 如果是其他错误
```
把错误日志发给我，我会帮你分析
```

## 📊 预期结果

成功运行后：
1. 会创建一个 Issue，包含当天精选论文
2. README.md 会更新
3. GitHub 会通知所有 Watchers

## ⏰ 自动运行

默认每天 UTC 0:00（北京时间 8:00）自动运行。

修改时间：编辑 `.github/workflows/daily-papers.yml` 中的 cron 表达式。

## 🎯 现在就试试！

跳过本地测试，直接在 GitHub Actions 上运行！

```bash
git add .
git commit -m "feat: 使用 Google AI Studio 进行论文评分"
git push
```

然后去 GitHub 配置 Secret 并手动触发 workflow。
