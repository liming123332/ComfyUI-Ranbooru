## 目标与范围
- 将当前基于 WebUI Forge 的 `Ranbooru` 脚本迁移为 ComfyUI 可视化节点集，保留核心能力：Booru 搜索、提示词生成、标签清理/混合/乱序、评分排序、可选缓存与凭据管理。
- 第一版聚焦“生成正负提示词”与“可选拉取示例图片”，后续阶段再适配 LoRA 与 ControlNet 的 ComfyUI 原生连接方式。

## 节点设计
- RanbooruPrompt
  - 输入：`booru`、`tags`、`remove_bad_tags`、`remove_tags`、`change_background`、`change_color`、`shuffle_tags`、`change_dash`、`mix_prompt`、`mix_amount`、`mature_rating`、`sorting_order`、`limit_tags`、`max_tags`、`use_search_txt`、`search_file`、`use_remove_txt`、`remove_file`、`use_cache`、`api_key`、`user_id`
  - 输出：`positive_prompt(STRING)`、`negative_prompt(STRING)`
  - 说明：核心逻辑直接复用并改造成纯函数，参考 `generate_prompts_only` 和相关工具函数实现。
- RanbooruFetchImage（可选）
  - 输入：同上，额外支持 `post_id`、`max_pages`
  - 输出：`image(IMAGE)` 与 `metadata(JSON)`（包含 `file_url`、`tags`、`score` 等）
  - 说明：用于 ComfyUI 的 img2img 或 ControlNet 前级；仅拉取图片与元数据，不直接改写推理管线。
- RanbooruLoraSelect（后续阶段）
  - 输入：`folder`、`amount`、`min_weight`、`max_weight`、`custom_weights`、`lock_prev`
  - 输出：`lora_list(JSON)`（名称+权重）
  - 说明：不再向提示词注入 `<lora:...>`，而是输出给 ComfyUI 的 LoRA 相关节点（如 `Apply LoRA`）进行连接。

## 功能映射与代码参考
- Booru 访问层复用：`Gelbooru/Rule34/Safebooru/Danbooru/Konachan/Yandere/AIBooru/e621` 类，用于构造 URL、解析响应与 `tags/score/file_url` 标准化（scripts/ranbooru.py:176–541）。
- 提示词生成主流程：排序、混合、乱序、背景/配色附加、无效标签剔除、下划线替换、数量限制（scripts/ranbooru.py:1342–1516）。
- 负面提示与混沌模式：`generate_chaos`（scripts/ranbooru.py:543–567），`limit_prompt_tags`（scripts/ranbooru.py:652–668），在 ComfyUI 中按需输出 `negative_prompt` 字段。
- 缓存与凭据：`requests_cache`（可选）、`CredentialsManager`（scripts/ranbooru.py:35–91, 767–776, 1349–1372），迁移为节点内部读写 `user/credentials/credentials.json`。

## 技术实现
- 目录与文件
  - 新增 `__init__.py` 作为 ComfyUI 自定义节点入口，定义 `NODE_CLASS_MAPPINGS`、`NODE_DISPLAY_NAME_MAPPINGS`、`CATEGORY`。
  - 将 `scripts/ranbooru.py` 的通用逻辑（Booru 访问层、工具函数）抽到模块内，去除 Gradio/UI 依赖（如 `modules.scripts`、`InputAccordion`、A1111 的 `processing`、`deepbooru`、`controlnet`）。
- 节点接口
  - `INPUT_TYPES`: 使用 ComfyUI 约定，枚举与数值/字符串参数与默认值匹配原脚本。
  - `RETURN_TYPES`: Prompt 节点返回 `STRING, STRING`（正/负提示）；图片节点返回 `IMAGE, JSON`。
  - `FUNCTION`: 对应 `run`/`fetch` 等纯函数，不操作 ComfyUI 全局状态。
  - `OUTPUT_NODE`: Prompt 节点可设为输出节点以便直连 `CLIPTextEncode`。
- 依赖与健壮性
  - `requests` 必须；`requests_cache` 检测存在再启用，不强依赖。
  - 网络失败与空结果处理，保持与原脚本一致的回退逻辑（Rule34/Konachan/Yandere 无总数场景的二次拉取；scripts/ranbooru.py:268–297, 344–372, 383–416）。
- 行为差异调整
  - 移除 A1111 专属：`modules.processing`、`StableDiffusionProcessingImg2Img`、`deepbooru.model`、`controlnet external_code`。
  - `LoRAnado` 不再拼接 `<lora:...>`，改为返回列表供 ComfyUI LoRA 节点使用。

## 分阶段里程碑
- 阶段 1：完成 RanbooruPrompt 节点（正/负提示、评分排序、标签清理、缓存/凭据、文件标签输入）。
- 阶段 2：完成 RanbooruFetchImage 节点（图片与元数据输出，支持 `post_id`/分页与评分排序）。
- 阶段 3：完成 RanbooruLoraSelect 节点并提供示例工作流 JSON。
- 阶段 4：增强：`requests_cache` 开关、凭据 UI 提示、出错信息友好化、更多 Booru 兼容细节。

## 兼容性与依赖
- 不再依赖 A1111 的 `modules.*`、Gradio UI 与 `sd_hijack`；仅保留 HTTP 访问与简单文件读写。
- 依赖：`requests`（必需）、`requests_cache`（可选）。凭据存储位置沿用 `user/credentials/credentials.json`。

## 验证方式
- 提供两个最小 ComfyUI workflow 示例：
  - Prompt 直连：`RanbooruPrompt -> CLIPTextEncode -> KSampler`。
  - 图片辅助：`RanbooruFetchImage -> VAE Encode -> KSampler` 与 `RanbooruPrompt -> CLIPTextEncode`。
- 加入已知标签与 `post_id` 的回归用例，验证排序与标签过滤结果。

## 需要确认
- 是否需要第一版就支持 `deepbooru` 自动打标与 ControlNet 注入；若需要，将以独立节点实现并与现有 ComfyUI 节点组合，而非复用 A1111 专属路径。
