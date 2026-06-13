import logging
import requests

logger = logging.getLogger(__name__)


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

    def generate_notes(self, text: str) -> str:
        """Second pass: generate structured Markdown notes."""
        system = (
            "你是一个知识整理专家。请根据以下文本生成结构化的 Markdown 笔记：\n\n"
            "## 📝 摘要\n"
            "用 3-5 句话概括核心内容\n\n"
            "## 📌 核心要点\n"
            "- 用列表列出关键观点和结论\n\n"
            "## ⏱️ 内容时间线\n"
            "如果有时间相关的先后顺序，按时间线整理\n\n"
            "## 💡 关键术语/概念\n"
            "- 解释文中出现的重要术语\n\n"
            "请使用简洁的中文，适当使用 emoji 提升可读性。"
        )
        return self._call(system, text)
