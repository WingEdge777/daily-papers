# GitHub Actions 设置指南

## 1. 配置 API Key

进入仓库 Settings → Secrets and variables → Actions，添加：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API密钥 | [获取地址](https://openrouter.ai/keys) |

**获取 OpenRouter API Key：**
1. 访问 https://openrouter.ai
2. 注册账号（支持 GitHub / Google 登录）
3. 进入 Settings → Keys
4. 点击 **Create Key**
5. 复制密钥（格式：`sk-or-...`）

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

## 7. 自动模型选择

系统会自动选择 OpenRouter 最热门的免费模型：

- 每次运行时自动获取免费模型列表
- 按使用量排序，选择最热门的模型
- 无需手动配置

**手动指定模型：**

编辑 `config.yaml`：

```yaml
llm:
  openrouter:
    model: "google/gemma-4-31b"  # 指定模型
```

## 故障排查

### API Key 无效
- 检查 Secret 名称是否正确（`OPENROUTER_API_KEY`，区分大小写）
- 检查 API Key 是否有效（在 OpenRouter 控制台测试）

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
- 系统会自动 fallback 到默认模型：`nvidia/nemotron-3-super`
- 查看日志中的 "Auto-selected model" 信息

## 成本

**完全免费！**

- OpenRouter 有多个永久免费的模型
- 系统自动选择最热门的免费模型
- 每日运行成本：$0
