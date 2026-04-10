"""将 LLM 返回的分类对齐到配置中的关键词。"""

from difflib import get_close_matches
from typing import List


def resolve_category(raw: str, keywords: List[str]) -> str:
    """
    将模型输出的 category 映射为 config.keywords 中的标准项。

    依次尝试：精确匹配、忽略大小写、模糊匹配、较长关键词的子串包含。
    """
    text = (raw or "").strip()
    if not text:
        return ""

    for kw in keywords:
        if text == kw:
            return kw

    lower = text.lower()
    for kw in keywords:
        if lower == kw.lower():
            return kw

    close = get_close_matches(text, keywords, n=1, cutoff=0.72)
    if close:
        return close[0]

    # 较长关键词优先，减少误匹配
    for kw in sorted(keywords, key=len, reverse=True):
        if len(kw) < 8:
            continue
        kl = kw.lower()
        if lower in kl or kl in lower:
            return kw

    return ""
