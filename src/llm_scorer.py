import os
import json
import re
import time
from typing import Dict, List, Optional, Set, Tuple
import requests

from src.logger import logger


class LLMScorer:
    """LLM paper scorer"""
    
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
        self.fallback_model = self._get("fallback_model", "gemini-3.0-flash")
        self.priority_models = self._get("priority_models", [
            "gemini-3.0-flash",
            "gemma-3-4b-it",
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
        """Auto-select best available model"""
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
        """Test if model is available"""
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
        """Switch to next available model without testing (to avoid wasting quota)"""
        self.rate_limited_models.add(self.model)
        
        for model in self.priority_models:
            if model not in self.rate_limited_models:
                logger.info(f"Switching model: {self.model} → {model}")
                self.model = model
                return model
        
        return None
    
    def score_paper(self, title: str, abstract: str, keywords: List[str]) -> Tuple[float, str, str, str]:
        """
        Score and categorize paper
        
        Returns:
            (score, summary, reason, category): score (0-100), summary, reason, matched category
        """
        prompt = self._build_prompt(title, abstract, keywords)
        max_parse_retries = 2

        for attempt in range(max_parse_retries):
            try:
                response = self._call_api(prompt)
                score, summary, reason, category = self._parse_response(response)
                if score > 0 or summary or reason or category:
                    logger.info(f"Scored paper '{title[:50]}...': {score}/100, category: {category}")
                    return score, summary, reason, category
                if attempt < max_parse_retries - 1:
                    logger.warning("Failed to parse LLM response, retrying...")
            except Exception as e:
                logger.error(f"Failed to score paper: {e}")
                if attempt >= max_parse_retries - 1:
                    break

        logger.info(f"Scored paper '{title[:50]}...': 0.0/100, category: ")
        return 0.0, "", "", ""
    
    def _build_prompt(self, title: str, abstract: str, keywords: List[str]) -> str:
        keywords_str = "、".join(keywords)
        return f"""请对这篇学术论文进行严格评分、总结和分类。

标题: {title}

摘要: {abstract}

可选分类: {keywords_str}

请从以下角度评估（每项0-25分，请严格评分，大部分论文应在60-80分区间）：

1. 创新性（0-25分）：
   - 20-25分：重大突破或全新方法
   - 15-19分：有意义的改进
   - 10-14分：常规应用或小改进
   - 0-9分：无明显创新

2. 实用性（0-25分）：
   - 20-25分：有重要应用价值
   - 15-19分：有一定应用潜力
   - 10-14分：应用场景有限
   - 0-9分：缺乏实用价值

3. 严谨性（0-25分）：
   - 20-25分：方法合理，实验充分
   - 15-19分：方法基本合理，实验尚可
   - 10-14分：存在明显不足
   - 0-9分：方法有严重缺陷

4. 清晰度（0-25分）：
   - 20-25分：表述清晰，逻辑严密
   - 15-19分：基本清晰
   - 10-14分：表述一般
   - 0-9分：难以理解

评分指导：
- 只有少数优秀论文才能达到85分以上
- 大部分合格论文应在60-80分区间
- 质量一般或有明显缺陷的论文应低于60分

总分 = 四项得分之和（0-100分）

请严格按以下JSON格式回复（不要有其他内容）：
{{
    "score": <0-100的整数>,
    "summary": "<一句话总结论文核心贡献，30字以内>",
    "reason": "<评分理由，50字以内>",
    "category": "<最贴近的分类，从可选分类中选一个>"
}}"""
    
    def _call_api(self, prompt: str) -> Dict:
        """Call Google AI Studio API with model rotation and retry logic.
        
        Model switching (429/404) does not consume retry count.
        Only "all models exhausted" cycles and timeouts count as retries.
        """
        self.rate_limited_models.clear()
        self.unavailable_models: Set[str] = set()
        retries = 0
        
        while retries < self.max_retries:
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key,
            }
            
            gen_config: Dict = {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
            }
            if self.model.startswith("gemini"):
                gen_config["responseMimeType"] = "application/json"

            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": gen_config,
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
                    
                    retries += 1
                    logger.warning(
                        f"All models rate limited, waiting {self.retry_delay_429}s... "
                        f"({retries}/{self.max_retries})"
                    )
                    time.sleep(self.retry_delay_429)
                    self.rate_limited_models = self.unavailable_models.copy()
                    first_available = next(
                        (m for m in self.priority_models if m not in self.unavailable_models),
                        self.priority_models[0]
                    )
                    self.model = first_available
                    continue
                
                if response.status_code in (404, 400):
                    error_detail = response.text[:200]
                    logger.warning(f"Model {self.model} unavailable ({response.status_code}): {error_detail}")
                    self.unavailable_models.add(self.model)
                    self.rate_limited_models.add(self.model)
                    if self._switch_model():
                        continue
                    raise requests.exceptions.HTTPError(
                        f"No available model, last error: {response.status_code}"
                    )
                
                if response.status_code in (502, 503):
                    retries += 1
                    logger.warning(
                        f"Service error ({response.status_code}), waiting {self.retry_delay_503}s... "
                        f"({retries}/{self.max_retries})"
                    )
                    time.sleep(self.retry_delay_503)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                retries += 1
                logger.warning(f"Timeout, retrying... ({retries}/{self.max_retries})")
                time.sleep(self.retry_delay_timeout)
                continue
            except requests.exceptions.HTTPError:
                raise
        
        raise Exception("Max retries exceeded")
    
    def _parse_response(self, response: Dict) -> Tuple[float, str, str, str]:
        """Parse API response"""
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
            category = result.get("category", "")
            
            return score, summary, reason, category
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            logger.error(f"Response content: {content[:500] if content else 'N/A'}")
            return 0.0, "", "", ""
