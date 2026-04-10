import os
import json
import re
import time
from typing import Dict, Optional, Tuple
import requests
from .logger import logger


class LLMScorer:
    """LLM论文评分器"""
    
    def __init__(self, config: Optional[Dict] = None):
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
        """获取模型，自动选择可用的 Flash 模型"""
        model = self.config.get("model")
        if model and model != "auto":
            return model
        
        return self._select_best_model()
    
    def _select_best_model(self) -> str:
        """自动选择最佳可用模型"""
        try:
            url = f"{self._get_base_url()}/models?key={self.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            models = response.json().get("models", [])
            available_models = {m["name"].replace("models/", ""): m for m in models}
            
            # 测试每个模型是否能正常使用
            test_prompt = "Reply with: OK"
            
            # 优先级列表 - 根据你的配额调整顺序
            # 查看配额: https://aistudio.google.com/rate-limit?timeRange=last-28-days
            priority_models = [
                "gemini-3.1-flash-lite-preview",  # 15 RPM, 250K daily
                "gemini-2.5-flash-lite",          # 10 RPM, 250K daily
                "gemini-2.5-flash",               # 可能限流
                "gemini-2.0-flash",               
            ]
            
            for model in priority_models:
                if model in available_models:
                    # 测试模型是否可用
                    if self._test_model(model, test_prompt):
                        logger.info(f"Auto-selected model: {model}")
                        return model
            
            # 如果优先模型都不可用，尝试其他 flash 模型
            for name, m in available_models.items():
                if "flash" in name.lower() and "generateContent" in m.get("supportedGenerationMethods", []):
                    if self._test_model(name, test_prompt):
                        logger.info(f"Auto-selected model: {name}")
                        return name
            
            raise Exception("No suitable model found")
            
        except Exception as e:
            logger.warning(f"Failed to auto-select model: {e}, using gemini-2.5-flash")
            return "gemini-2.5-flash"
    
    def _test_model(self, model: str, prompt: str) -> bool:
        """测试模型是否可用"""
        try:
            url = f"{self._get_base_url()}/models/{model}:generateContent"
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
    
    def _get_base_url(self) -> str:
        return self.config.get("base_url", "https://generativelanguage.googleapis.com/v1beta")
    
    def score_paper(self, title: str, abstract: str) -> Tuple[float, str, str]:
        """
        对论文进行评分和摘要
        
        Returns:
            (score, summary, reason): 评分(1-10)、摘要、评分理由
        """
        prompt = self._build_prompt(title, abstract)
        
        try:
            response = self._call_api(prompt)
            score, summary, reason = self._parse_response(response)
            logger.info(f"Scored paper '{title[:50]}...': {score}/100")
            return score, summary, reason
        except Exception as e:
            logger.error(f"Failed to score paper: {e}")
            return 0.0, "", ""
    
    def _build_prompt(self, title: str, abstract: str) -> str:
        return f"""请对这篇学术论文进行评分和总结。

标题: {title}

摘要: {abstract}

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
    "reason": "<评分理由，50字以内>"
}}"""
    
    def _call_api(self, prompt: str) -> Dict:
        """调用 Google AI Studio API"""
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
                "temperature": 0.3,
                "maxOutputTokens": 2048
            }
        }
        
        max_retries = 3
        response = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code == 429:
                    error_detail = response.text
                    logger.warning(f"Rate limited (429): {error_detail}")
                    logger.warning(f"Waiting 60s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(60)
                    continue
                
                if response.status_code == 503:
                    logger.warning(f"Service unavailable (503), waiting 10s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(10)
                    continue
                
                if response.status_code == 400:
                    error_detail = response.text
                    logger.error(f"Bad Request (400): {error_detail}")
                    raise requests.exceptions.HTTPError(f"400 Bad Request: {error_detail}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if attempt < max_retries - 1 and response and response.status_code in [429, 503, 502]:
                    wait_time = 2 ** attempt * 5
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
    
    def _parse_response(self, response: Dict) -> Tuple[float, str, str]:
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
            
            return score, summary, reason
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            logger.error(f"Response content: {content[:500] if content else 'N/A'}")
            return 0.0, "", ""
