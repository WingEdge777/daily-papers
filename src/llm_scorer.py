import os
import json
import re
import time
from typing import Dict, List, Optional, Set, Tuple
import requests
from .logger import logger


class LLMScorer:
    """LLM论文评分器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = self._get_api_key()
        self.base_url = self._get("base_url", "https://generativelanguage.googleapis.com/v1beta")
        
        self.temperature = self._get("temperature", 0.3)
        self.max_output_tokens = self._get("max_output_tokens", 2048)
        self.timeout = self._get("timeout", 60)
        self.max_retries = self._get("max_retries", 3)
        self.retry_delay_429 = self._get("retry_delay_429", 10)
        self.retry_delay_503 = self._get("retry_delay_503", 10)
        self.retry_delay_timeout = self._get("retry_delay_timeout", 5)
        self.fallback_model = self._get("fallback_model", "gemini-2.5-flash")
        self.priority_models = self._get("priority_models", [
            "gemini-3.1-flash-lite-preview",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemma-4-31B",
        ])
        
        self.model = self._get_model()
        self.rate_limited_models: Set[str] = set()
    
    def _get(self, key: str, default):
        return self.config.get(key, default)
    
    def _get_api_key(self) -> str:
        key = self.config.get("api_key", "")
        if key.startswith("${") and key.endswith("}"):
            env_var = key[2:-1]
            return os.getenv(env_var, "")
        return key
    
    def _get_model(self) -> str:
        model = self.config.get("model")
        if model and model != "auto":
            return model
        return self._select_best_model()
    
    def _select_best_model(self, excluded: Optional[Set[str]] = None) -> str:
        """自动选择最佳可用模型"""
        excluded = excluded or set()
        
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            models = response.json().get("models", [])
            available_models = {m["name"].replace("models/", ""): m for m in models}
            
            test_prompt = "Reply with: OK"
            
            for model in self.priority_models:
                if model in available_models and model not in excluded:
                    if self._test_model(model, test_prompt):
                        logger.info(f"Auto-selected model: {model}")
                        return model
            
            for name, m in available_models.items():
                if name not in excluded and "flash" in name.lower() and "generateContent" in m.get("supportedGenerationMethods", []):
                    if self._test_model(name, test_prompt):
                        logger.info(f"Auto-selected model: {name}")
                        return name
            
            raise Exception("No suitable model found")
            
        except Exception as e:
            logger.warning(f"Failed to auto-select model: {e}, using {self.fallback_model}")
            return self.fallback_model
    
    def _test_model(self, model: str, prompt: str) -> bool:
        """测试模型是否可用"""
        try:
            url = f"{self.base_url}/models/{model}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key,
            }
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 10}
            }
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 429:
                logger.debug(f"Model {model} rate limited")
                return False
            else:
                logger.debug(f"Model {model} failed: {response.status_code}")
                return False
        except Exception as e:
            logger.debug(f"Model {model} test failed: {e}")
            return False
    
    def _switch_model(self) -> Optional[str]:
        """切换到下一个可用模型"""
        self.rate_limited_models.add(self.model)
        
        remaining = [m for m in self.priority_models if m not in self.rate_limited_models]
        
        if remaining:
            for model in remaining:
                if self._test_model(model, "OK"):
                    logger.info(f"Switched model: {self.model} → {model}")
                    self.model = model
                    return model
        
        return None
    
    def score_paper(self, title: str, abstract: str, keywords: List[str]) -> Tuple[float, str, str, List[str]]:
        """
        对论文进行评分和分类
        
        Returns:
            (score, summary, reason, keywords): 评分(0-100)、摘要、评分理由、匹配的关键词列表
        """
        prompt = self._build_prompt(title, abstract, keywords)
        
        try:
            response = self._call_api(prompt)
            score, summary, reason, matched_keywords = self._parse_response(response)
            logger.info(f"Scored paper '{title[:50]}...': {score}/100, keywords: {matched_keywords}")
            return score, summary, reason, matched_keywords
        except Exception as e:
            logger.error(f"Failed to score paper: {e}")
            return 0.0, "", "", []
    
    def _build_prompt(self, title: str, abstract: str, keywords: List[str]) -> str:
        keywords_str = "、".join(keywords)
        return f"""请对这篇学术论文进行评分、总结和分类。

标题: {title}

摘要: {abstract}

可选分类: {keywords_str}

请从以下角度评估（每项0-25分）：
1. 创新性：是否提出新方法/新视角
2. 实用性：是否有实际应用价值
3. 严谨性：方法是否合理，实验是否充分
4. 清晰度：写作是否清晰易懂

总分 = 四项得分之和（0-100分）

请严格按以下JSON格式回复（不要有其他内容）：
{{
    "score": <0-100的整数>,
    "summary": "<一句话总结论文核心贡献，30字以内>",
    "reason": "<评分理由，50字以内>",
    "keywords": ["<匹配的分类，从可选分类中选择，可多选>"]
}}"""
    
    def _call_api(self, prompt: str) -> Dict:
        """调用 Google AI Studio API"""
        
        for retry in range(self.max_retries):
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key,
            }
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_output_tokens
                }
            }
            
            response = None
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )
                
                if response.status_code == 429:
                    logger.warning(f"Model {self.model} rate limited (429)")
                    
                    if self._switch_model():
                        continue
                    
                    logger.warning(f"All models rate limited, waiting {self.retry_delay_429}s...")
                    time.sleep(self.retry_delay_429)
                    self.rate_limited_models.clear()
                    continue
                
                if response.status_code == 503:
                    logger.warning(f"Service unavailable (503), waiting {self.retry_delay_503}s...")
                    time.sleep(self.retry_delay_503)
                    continue
                
                if response.status_code == 400:
                    error_detail = response.text
                    logger.error(f"Bad Request (400): {error_detail}")
                    raise requests.exceptions.HTTPError(f"400 Bad Request: {error_detail}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout, retrying... ({retry + 1}/{self.max_retries})")
                time.sleep(self.retry_delay_timeout)
                continue
            except requests.exceptions.HTTPError as e:
                if response and response.status_code in [502, 503]:
                    time.sleep(self.retry_delay_503)
                    continue
                raise
        
        raise Exception("Max retries exceeded")
    
    def _parse_response(self, response: Dict) -> Tuple[float, str, str, List[str]]:
        """解析API响应"""
        content = ""
        try:
            content = response["candidates"][0]["content"]["parts"][0]["text"]
            
            logger.debug(f"Raw response: {content}")
            
            content = content.strip()
            
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            elif content.startswith("```"):
                lines = content.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = '\n'.join(lines).strip()
            
            if '{' in content and '}' in content:
                start = content.index('{')
                end = content.rindex('}') + 1
                content = content[start:end]
            
            result = json.loads(content)
            score = float(result.get("score", 0))
            summary = result.get("summary", "")
            reason = result.get("reason", "")
            keywords = result.get("keywords", [])
            
            return score, summary, reason, keywords
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            logger.error(f"Response content: {content[:500] if content else 'N/A'}")
            return 0.0, "", "", []
