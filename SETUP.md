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

## 3. 配置 Workflow 权限

**重要：Fork 的仓库需要额外配置权限才能提交代码。**

1. 进入仓库 **Settings**
2. 左侧菜单选择 **Actions** → **General**
3. 滚动到 **Workflow permissions**
4. 选择 **Read and write permissions**
5. 点击 **Save**

## 4. 手动测试

1. 进入 **Actions** → **Daily Papers**
2. 点击 **Run workflow** → **Run workflow**
3. 等待运行完成
4. 查看 `papers/` 目录，应该会创建一个新的日期文件

## 5. 自动运行

Workflow 已配置为每天 UTC 0:00（北京时间 8:00）自动运行。

## 6. 查看历史论文

所有历史论文保存在 `papers/` 目录，每天一个单独的 markdown 文件。

## 7. 接收邮件通知

点击仓库右上角 **Watch** → **All Activity**，即可收到每次运行的邮件通知。

## 8. 修改运行时间

编辑 `.github/workflows/daily-papers.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC时间
```

常用时间设置：
- `'0 0 * * *'` - UTC 0:00（北京时间 8:00）
- `'0 1 * * *'` - UTC 1:00（北京时间 9:00）
- `'0 23 * * *'` - UTC 23:00（北京时间次日 7:00）

## 9. 模型选择

默认自动选择可用的 Gemini 模型。

**手动指定模型：**

编辑 `config.yaml`：

```yaml
llm:
  google:
    model: "gemini-3.1-flash-lite-preview"  # 指定模型
```

## 故障排查

### API Key 无效
- 检查 Secret 名称是否正确（`GOOGLE_AI_API_KEY`，区分大小写）
- 检查 API Key 是否有效（在 Google AI Studio 测试）

### 没有论文输出
- 检查 ArXiv API 是否可访问
- 查看 Actions 日志中的错误信息

### 文件提交失败
- 检查 Workflow 权限设置（见步骤3）
- 确认选择了 **Read and write permissions**

### 模型选择失败
- 检查 Google AI API Key 是否有效
- 查看日志中的错误信息

## 成本

**完全免费！**

- Google AI Studio 每天 1500 次免费请求
- Gemini 2.0 Flash 快速且免费
- 每日运行成本：$0
