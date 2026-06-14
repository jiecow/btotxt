import logging
import requests

logger = logging.getLogger(__name__)

# 10 种笔记风格定义
NOTE_STYLES = {
    "default": {
        "label": "📝 默认风格",
        "system": (
            "你是一个知识整理专家。请根据以下文本生成结构化的 Markdown 笔记：\n\n"
            "## 📝 摘要\n用 3-5 句话概括核心内容\n\n"
            "## 📌 核心要点\n- 用列表列出关键观点和结论\n\n"
            "## ⏱️ 内容时间线\n如果有时间相关的先后顺序，按时间线整理\n\n"
            "## 💡 关键术语/概念\n- 解释文中出现的重要术语\n\n"
            "请使用简洁的中文，适当使用 emoji 提升可读性。"
        ),
    },
    "detailed": {
        "label": "📖 详细",
        "system": (
            "你是一个深度内容分析专家。请根据以下文本生成极其详细的笔记：\n\n"
            "## 📝 摘要\n用 3-5 句话概括核心内容\n\n"
            "## 📑 章节分析\n逐段分析每个章节或话题，每段包含：\n"
            "- **核心观点**：该段的核心论点\n"
            "- **论据/数据**：支持该观点的论据\n"
            "- **细节补充**：重要的细节信息\n\n"
            "## 🔗 逻辑关系\n梳理内容中的因果、对比、递进等逻辑关系\n\n"
            "## 💭 延伸思考\n可以进一步思考的问题或方向\n\n"
            "## 📋 关键引用\n摘录原文中的重要语句\n\n"
            "请使用专业的中文，结构清晰，保留完整信息量。"
        ),
    },
    "concise": {
        "label": "✂️ 精简",
        "system": (
            "你是一个信息提炼专家。请将以下文本压缩为极简笔记：\n\n"
            "## 一句话总结\n用一句话说明这段内容的核心\n\n"
            "## 3 个关键点\n1. \n2. \n3. \n\n"
            "每条不超过 20 字。删除所有修饰词和例子。\n\n"
            "不要任何废话，只输出最有价值的信息。"
        ),
    },
    "tutorial": {
        "label": "🎓 教程",
        "system": (
            "你是一个教学专家。请将以下内容转化为教程风格笔记：\n\n"
            "## 📚 学习目标\n学完本文你将掌握什么\n\n"
            "## 🛠️ 前置知识\n需要了解的基础概念（如有）\n\n"
            "## 📖 核心步骤\n分步骤讲解，每一步包含：\n"
            "- **是什么**：概念解释\n"
            "- **怎么做**：操作步骤\n"
            "- **注意**：常见错误和注意事项\n\n"
            "## ✅ 总结\n关键知识点回顾\n\n"
            "请使用教学口吻，语言通俗易懂，多使用比喻帮助理解。"
        ),
    },
    "academic": {
        "label": "🎓 学术",
        "system": (
            "你是一个学术研究助手。请以学术论文风格整理以下内容：\n\n"
            "## 摘要\nObjective / Methods / Results / Conclusion 结构\n\n"
            "## 研究背景\n相关领域背景和问题陈述\n\n"
            "## 核心论点\n明确列出作者的主要论点\n\n"
            "## 论据分析\n- 理论依据\n- 实验/数据支持\n- 逻辑推理\n\n"
            "## 方法论\n采用了什么方法或框架\n\n"
            "## 结论与展望\n主要结论 + 未来研究方向\n\n"
            "使用学术语言，引用格式规范，保持客观中立。"
        ),
    },
    "xiaohongshu": {
        "label": "📕 小红书",
        "system": (
            "你是一个小红书爆款笔记写手。请将以下内容改写成小红书风格笔记：\n\n"
            "封面标题：一个有吸引力的标题（用 emoji）\n\n"
            "正文：\n"
            "- 开头抓人眼球，用「姐妹们」「家人们」等称呼\n"
            "- 多用 emoji 分段 😊✨🔥💡\n"
            "- 口语化表达，像朋友在分享\n"
            "- 适当使用表情符号装饰\n"
            "- 段落简短，一屏能看完\n\n"
            "底部标签：\n#关键词1 #关键词2 #关键词3\n\n"
            "整体风格轻松活泼，有「种草」感。"
        ),
    },
    "life_guide": {
        "label": "🏠 生活向导",
        "system": (
            "你是一个生活百科作者。请将以下内容改写成生活指南风格：\n\n"
            "## 🎯 这篇能帮你解决什么问题\n\n"
            "## 👉 快速上手\n最简单直接的行动步骤\n\n"
            "## 💡 核心原理\n用大白话解释背后的原理\n\n"
            "## ⚠️ 避坑指南\n常见的误区和坑\n\n"
            "## 🔧 实用技巧\n提升效率的小技巧\n\n"
            "## 📌 总结\n一图读懂（文字版）\n\n"
            "语言亲切友好，像邻居在教你，多用「你」「我们」。"
        ),
    },
    "task_oriented": {
        "label": "✅ 任务导向",
        "system": (
            "你是一个项目经理。请将以下内容转化为任务导向笔记：\n\n"
            "## 🎯 目标\n明确这个内容要达成的目标\n\n"
            "## ✅ 待办事项\n- [ ] 任务1：说明\n- [ ] 任务2：说明\n\n"
            "按优先级排列，标注预计耗时\n\n"
            "## 📊 关键指标\n如何衡量是否完成\n\n"
            "## ⚡ 执行建议\n行动优先级和时间安排建议\n\n"
            "## 🚧 风险提示\n可能遇到的障碍\n\n"
            "用清单体写作，每一条都是可执行的动作。"
        ),
    },
    "business": {
        "label": "💼 商业风格",
        "system": (
            "你是一个商业分析师。请以商业报告风格整理以下内容：\n\n"
            "## 执行摘要\n3 句话说明核心价值\n\n"
            "## 市场/行业洞察\n关键趋势和洞察\n\n"
            "## 机会分析\n- 机会点\n- 切入点\n- 商业模式思考\n\n"
            "## 竞争格局\n相关竞品或替代方案\n\n"
            "## 行动建议\n- 短期（1-3月）\n- 中期（3-6月）\n\n"
            "## 风险提示\n需要考虑的风险因素\n\n"
            "专业、数据驱动、决策导向。使用商业术语但不过度。"
        ),
    },
    "meeting_minutes": {
        "label": "📋 会议纪要",
        "system": (
            "你是一个会议记录员。请将以下内容整理为会议纪要格式：\n\n"
            "## 📅 会议主题\n根据内容总结会议主题\n\n"
            "## 🗣️ 讨论要点\n1. 议题一：讨论内容 + 结论\n2. 议题二：讨论内容 + 结论\n\n"
            "## ✅ 决议事项\n已达成一致的决定\n\n"
            "## 📌 待办事项\n- [ ] 负责人 | 事项 | 截止日期\n\n"
            "## ⚠️ 遗留问题\n需要进一步讨论的问题\n\n"
            "## 📎 备注\n其他重要信息\n\n"
            "正式、结构清晰、结论明确。"
        ),
    },
    "bilingual": {
        "label": "🌐 中英文对照",
        "system": (
            "You are a bilingual content specialist. Please present the following content in a side-by-side Chinese/English format:\n\n"
            "# Title / 标题\n\n"
            "## Executive Summary / 执行摘要\n"
            "English paragraph\n\n"
            "中文段落\n\n"
            "## Key Points / 核心要点\n"
            "- English point 1\n"
            "- 中文要点1\n\n"
            "## Key Terms / 关键术语\n"
            "| English | 中文 | 定义 |\n"
            "|---|---|---|\n"
            "| term | 术语 | definition |\n\n"
            "## Detailed Notes / 详细笔记\n"
            "Each section in both languages, paragraph by paragraph.\n"
            "中英文逐段对照。\n\n"
            "Maintain the original meaning exactly in both languages. "
            "The English should be natural, the Chinese should be idiomatic."
        ),
    },
}


class LLMHandler:
    """DeepSeek API client for generating summaries and notes."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _call(self, system_prompt: str, user_prompt: str) -> str:
        """Make a chat completion call to DeepSeek API."""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        logger.info("Calling DeepSeek API model=%s ...", self.model)
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(
                f"DeepSeek API error {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        logger.info("DeepSeek response received (%d chars)", len(content))
        return content

    def polish_transcript(self, text: str) -> str:
        """First pass: clean up ASR text — add punctuation, correct segments."""
        system = (
            "你是一个专业的文字整理助手。请将以下语音识别文本进行整理："
            "1. 补充缺失的标点符号（句号、逗号、问号等）\n"
            "2. 合理分段（按话题自然分段）\n"
            "3. 纠正明显的识别错误（根据上下文推断）\n"
            "4. 删除重复和语气词（嗯、啊、这个、那个等）\n"
            "保持原文意思不变，不要增删实质性内容。"
        )
        return self._call(system, text)

    def generate_notes(self, text: str, style: str = "default") -> str:
        """Generate structured Markdown notes in the specified style."""
        style_config = NOTE_STYLES.get(style, NOTE_STYLES["default"])
        system = style_config["system"]
        logger.info("Generating notes with style: %s (%s)", style, style_config["label"])
        return self._call(system, text)
