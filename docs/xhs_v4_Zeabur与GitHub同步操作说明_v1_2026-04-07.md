# xhs_v4 Zeabur 与 GitHub 同步操作说明

- 文档版本：`v1.0`
- 日期：`2026-04-07`
- 适用对象：`当前 xhs_v4 Zeabur 环境 + GitHub Desktop 本地同步`

## 1. 当前环境结论

从当前 Zeabur 截图看，已经具备：

1. `xhs-v4` Web 服务
2. `postgresql` 数据库服务
3. `redis` 队列服务
4. 关键变量已配置：
   - `DATABASE_URL`
   - `REDIS_URL`
   - `CELERY_BROKER_URL`
   - `CELERY_RESULT_BACKEND`
   - `SECRET_KEY`
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD`
   - `DEEPSEEK_API_KEY`
   - `DEFAULT_TOPIC_QUOTA`

当前还差：

1. 单独的 `worker` 服务
2. 单独的 `beat` 服务
3. 如果要启用真实文生图，还需要补图片模型变量

## 2. Zeabur 下一步

### 2.1 新增 Worker 服务

建议新增一个服务：

1. 服务名：`xhs-v4-worker`
2. 代码来源：与 `xhs-v4` 相同仓库
3. 启动命令：`./docker/entrypoint-worker.sh`

Worker 需要复用 Web 服务的这些变量：

1. `DATABASE_URL`
2. `REDIS_URL`
3. `CELERY_BROKER_URL`
4. `CELERY_RESULT_BACKEND`
5. `SECRET_KEY`
6. `DEEPSEEK_API_KEY`
7. `DEFAULT_TOPIC_QUOTA`

### 2.2 可选图片模型变量

如果后面要把图片任务从 SVG 兜底升级为真实 AI 出图，再补：

1. `ASSET_IMAGE_PROVIDER`
2. `ASSET_IMAGE_API_URL`
3. `ASSET_IMAGE_API_KEY`
4. `ASSET_IMAGE_MODEL`
5. `ASSET_IMAGE_SIZE`

建议默认值参考：

```env
ASSET_IMAGE_PROVIDER=svg_fallback
ASSET_IMAGE_API_URL=
ASSET_IMAGE_API_KEY=
ASSET_IMAGE_MODEL=
ASSET_IMAGE_SIZE=1024x1536
```

其中 `ASSET_IMAGE_PROVIDER` 当前可用建议值：

1. `svg_fallback`
2. `openai`
3. `openai_compatible`
4. `generic_json`

说明：

1. `API Key` 仍建议留在 Zeabur 环境变量
2. `Provider / API URL / 模型 / 尺寸 / 热点默认参数` 现在可在后台自动化中心直接维护
3. 自动化中心还支持请求预览、任务详情和运行诊断
4. 图片任务结果会自动沉淀到图片资产库

### 2.3 新增 Beat 服务

如果你要启用自动调度，再新增一个服务：

1. 服务名：`xhs-v4-beat`
2. 代码来源：与 `xhs-v4` 相同仓库
3. 启动命令：`./docker/entrypoint-beat.sh`

Beat 需要复用这些变量：

1. `DATABASE_URL`
2. `REDIS_URL`
3. `CELERY_BROKER_URL`
4. `CELERY_RESULT_BACKEND`
5. `SECRET_KEY`
6. `ENABLE_AUTOMATION_BEAT`
7. `CELERY_BEAT_LOG_LEVEL`

## 3. GitHub Desktop 同步步骤

### 3.1 本地提交

在 GitHub Desktop 中：

1. 打开仓库 `xhs-v4`
2. 确认左侧文件变更列表
3. 填写 Summary，例如：
   `feat: add portal config, worker hotword skeleton and asset tasks`
4. 点击 `Commit to main`

### 3.2 推送到 GitHub

提交完成后：

1. 点击右上角 `Push origin`
2. 等待 GitHub 推送完成

### 3.3 让 Zeabur 自动拉取

如果 Zeabur 已绑定 GitHub 仓库，通常会自动触发部署。  
如果没有自动部署，就在 Zeabur 的 `xhs-v4` 服务里手动点击重新部署。

## 4. 推荐发布顺序

建议不要一次把所有服务都改掉，按下面顺序更稳：

1. 先推送 `web` 代码
2. 确认 `xhs-v4` Web 服务部署成功
3. 再新增 `xhs-v4-worker`
4. 再新增 `xhs-v4-beat`
5. 在自动化中心先点一次 `检测 Worker`
6. 再测试：
   - 候选话题异步生成
   - 热点抓取骨架任务
   - 图片生成任务
   - 自动调度配置

## 5. 当前代码已支持的云端能力

当前已经支持：

1. 门户配置与公告管理
2. 候选话题异步生成
3. 热点抓取 Worker 骨架任务
4. 图片生成 Worker 任务
5. 报名成功页一键图文创作包
6. 自动调度配置、暂停/恢复、立即执行

其中图片任务逻辑为：

1. 如果配置了图片模型变量，则优先调用外部图片服务
2. 如果未配置，则自动退回 `SVG` 配图兜底

## 6. 上线前检查清单

建议你在 Zeabur 上逐项确认：

1. Web 服务能打开 `/healthz`
2. 后台 `/admin`
3. 自动化中心 `/automation_center`
4. `Worker` 联通检查成功
5. 热点抓取任务能产生热点样例
6. 报名成功页能生成图文创作包
7. 图片任务能返回结果
8. 自动调度开启后能看到定时派发记录
9. 自动化中心“运行诊断”里环境项为已配置

## 7. 当前最值得继续做的两项

接下来优先建议：

1. 接真实图片模型服务，而不是只用 SVG 兜底
2. 给 Worker 增加定时调度、失败重试、暂停恢复
