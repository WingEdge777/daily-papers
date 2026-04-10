import os
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Optional, Tuple
import requests
from .logger import logger
from .model_selector import ModelSelector


class LLMScorer:
    """LLM论文评分器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.provider = "openrouter"
        self.config = config or {}
        self.api_key = self._get_api_key()
        self.model = self._get_model()
        self.base_url = self._get_base_url()
    
    def _get_api_key(self) -> str:
        key = self.config.get("api_key", "")
        if key.startswith("${") and key.endswith("}"):
            env_var = key[2:-1]
            return os.getenv(env_var, "")
        return key
    
    def _get_model(self) -> str:
        """获取模型，支持自动选择最热门的免费模型"""
        model = self.config.get("model")
        
        if model and model != "auto":
            return model
        
        # 自动选择最热门的免费模型
        return ModelSelector.get_best_free_model(self.api_key)
    
    def _get_base_url(self) -> str:
        return self.config.get("base_url", "https://openrouter.ai/api/v1")
    
    def score_paper(self, title: str, abstract: str) -> Tuple[float, str]:
        """
        对论文进行评分和摘要
        
        Returns:
            (score, summary): 评分(1-10)和摘要
        """
        prompt = self._build_prompt(title, abstract)
        
        try:
            response = self._call_llm(prompt)
            score, summary = self._parse_response(response)
            logger.info(f"Scored paper '{title[:50]}...': {score}/10")
            return score, summary
        except Exception as e:
            logger.error(f"Failed to score paper: {e}")
            return 0.0, ""
    
    def _build_prompt(self, title: str, abstract: str) -> str:
        return f"""请对这篇学术论文进行评分和总结。

标题: {title}

摘要: {abstract}

请从以下角度评估：
1. 创新性：是否提出新方法/新视角
2. 实用性：是否有实际应用价值
3. 严谨性：方法是否合理，实验是否充分
4. 清晰度：写作是否清晰易懂

请严格按以下JSON格式回复（不要有其他内容）：
{{
    "score": <1-10的整数>,
    "summary": "<一句话总结论文核心贡献，30字以内>",
    "reason": "<评分理由，50字以内>"
}}"""
    
    def _call_llm(self, prompt: str) -> Dict:
        """调用LLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/zezhishao/daily-papers"
            headers["X-OpenRouter-Title"] = "DailyPapers"
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 200
        }
        
        # 重试机制
        max_retries = 3
        response = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,  # 使用 json 参数，requests 会自动处理
                    timeout=60
                )
                
                if response.status_code == 429:
                    retry_after = self._parse_retry_after(response.headers.get("Retry-After"), 60)
                    logger.warning(f"Rate limited, waiting {retry_after}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_after)
                    continue
                
                # 如果是 400 错误，打印详细信息
                if response.status_code == 400:
                    error_detail = response.text
                    logger.error(f"Bad Request (400): {error_detail}")
                    raise requests.exceptions.HTTPError(f"400 Bad Request: {error_detail}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if attempt < max_retries - 1 and response and response.status_code in [429, 503, 502]:
                    wait_time = 2 ** attempt * 5  # 指数退避: 5s, 10s, 20s
                    logger.warning(f"Request failed, retrying in {wait_time}s... ({e})")
                    time.sleep(wait_time)
                    continue
                raise
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout, retrying... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(5)
                    continue
                raise
        
        raise Exception("Max retries exceeded")
    
    def _parse_retry_after(self, retry_after: Optional[str], default: int = 60) -> int:
        """解析 Retry-After header，支持整数秒和 HTTP 日期格式"""
        if not retry_after:
            return default
        
        try:
            return int(retry_after)
        except ValueError:
            pass
        
        try:
            retry_time = parsedate_to_datetime(retry_after)
            if retry_time:
                now = datetime.now(timezone.utc)
                diff = (retry_time - now).total_seconds()
                return max(int(diff), 0)
        except Exception:
            pass
        
        return default
    
    def _parse_response(self, response: Dict) -> Tuple[float, str]:
        """解析LLM响应"""
        try:
            content = response["choices"][0]["message"]["content"]
            
            # 提取JSON
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            score = float(result.get("score", 0))
            summary = result.get("summary", "")
            
            return score, summary
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return 0.0, ""
