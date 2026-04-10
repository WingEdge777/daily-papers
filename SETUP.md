# GitHub Actions 设置指南

## 1. 配置 API Key

进入仓库 Settings → Secrets and variables → Actions，添加：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `GOOGLE_AI_API_KEY` | Google AI Studio API密钥 | [获取地址](https://aistudio.google.com/apikey) |

**获取 Google AI API Key：**
1. 访问 https://aistudio.google.com/apikey
2. 点击 **Create API Key**
3. 复制生成的 API Key

## 2. 启用 GitHub Actions

1. 进入仓库的 **Actions** 标签页
2. 如果看到提示，点击 **I understand my workflows, go ahead and enable them**
3. 选择 **Daily Papers** workflow
4. 点击 **Enable workflow**

## 3. 手动测试

1. 进入 **Actions** → **Daily Papers**
2. 点击 **Run workflow** → **Run workflow**
3. 等待运行完成
4. 查看 **Issues** 标签页，应该会创建一个新的 Issue

## 4. 自动运行

Workflow 已配置为每天 UTC 0:00（北京时间 8:00）自动运行。

## 5. 接收通知

### 方式1：Watch 仓库
点击仓库右上角的 **Watch** → **All Activity**，即可收到每次运行的邮件通知。

### 方式2：订阅 Issues
仓库会自动创建每日论文 Issue，GitHub 会通知所有 Watchers。

## 6. 修改运行时间

编辑 `.github/workflows/daily-papers.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC时间
```

常用时间设置：
- `'0 0 * * *'` - UTC 0:00（北京时间 8:00）
- `'0 1 * * *'` - UTC 1:00（北京时间 9:00）
- `'0 23 * * *'` - UTC 23:00（北京时间次日 7:00）

## 7. 模型选择

默认使用 **Gemini 2.0 Flash**，免费且快速。

**手动指定模型：**

编辑 `config.yaml`：

```yaml
llm:
  google:
    model: "gemini-1.5-pro"  # 更强大的模型
```

可用模型：
- `gemini-2.0-flash` - 最新，快速（推荐）
- `gemini-1.5-flash` - 稳定，快速
- `gemini-1.5-pro` - 更强大，稍慢

## 故障排查

### API Key 无效
- 检查 Secret 名称是否正确（`GOOGLE_AI_API_KEY`，区分大小写）
- 检查 API Key 是否有效（在 Google AI Studio 测试）

### 没有论文输出
- 检查 ArXiv API 是否可访问
- 查看 Actions 日志中的错误信息

### Issue 创建失败
- 检查仓库是否有 Issues 功能启用
- 检查 GitHub Token 权限

### 邮件没有收到
- 确认已 Watch 仓库
- 检查 GitHub 邮件通知设置（Settings → Notifications）
- 检查邮箱垃圾邮件文件夹

### 模型选择失败
- 检查 Google AI API Key 是否有效
- 查看日志中的错误信息

## 成本

**完全免费！**

- Google AI Studio 每天 1500 次免费请求
- Gemini 2.0 Flash 快速且免费
- 每日运行成本：$0
