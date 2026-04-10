import os
import requests
from typing import Optional, List, Dict
from .logger import logger


class ModelSelector:
    """自动选择OpenRouter最热门的免费模型"""
    
    OPENROUTER_API = "https://openrouter.ai/api/v1/models"
    CACHE_FILE = "/tmp/openrouter_free_models.json"
    
    @classmethod
    def get_best_free_model(cls, api_key: Optional[str] = None) -> str:
        """
        获取最热门的免费模型
        
        优先级：
        1. 使用量最高（most popular）
        2. 价格为 $0
        3. 排除 OCR、Embedding 等特殊模型
        """
        try:
            models = cls._fetch_free_models(api_key)
            
            if models:
                # 过滤掉 openrouter/free（这是个路由器，不是真实模型）
                valid_models = [m for m in models if m['id'] != 'openrouter/free']
                
                if valid_models:
                    # 优先选择已知的稳定模型
                    preferred_models = [
                        "meta-llama/llama-3.3-70b-instruct:free",
                        "google/gemma-3-27b-it:free",
                        "nvidia/nemotron-3-super-120b-a12b:free",
                        "google/gemma-4-31b-it:free",
                    ]
                    
                    for preferred in preferred_models:
                        for model in valid_models:
                            if preferred == model['id']:
                                logger.info(f"Auto-selected model: {model['id']}")
                                return model['id']
                    
                    # 如果没有找到优先模型，选择第一个有效模型
                    best_model = valid_models[0]
                    logger.info(f"Auto-selected model: {best_model['id']}")
                    return best_model['id']
        except Exception as e:
            logger.warning(f"Failed to fetch free models: {e}, using fallback")
        
        # Fallback: 使用已知的稳定免费模型
        logger.info("Using fallback model: meta-llama/llama-3.3-70b-instruct:free")
        return "meta-llama/llama-3.3-70b-instruct:free"
    
    @classmethod
    def _fetch_free_models(cls, api_key: Optional[str] = None) -> List[Dict]:
        """从OpenRouter API获取免费模型列表"""
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            response = requests.get(
                cls.OPENROUTER_API,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to fetch models from API: {e}")
            return []
        
        data = response.json()
        models = data.get("data", [])
        
        # 过滤免费模型
        free_models = []
        for model in models:
            try:
                pricing = model.get("pricing", {})
                
                # 处理价格字段（可能是字符串或数字）
                def parse_price(val):
                    if val is None:
                        return 0.0
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0
                
                input_price = parse_price(pricing.get("prompt"))
                output_price = parse_price(pricing.get("completion"))
                
                # 只选择完全免费的模型
                if input_price == 0 and output_price == 0:
                    model_id = model.get("id", "")
                    
                    # 排除特殊模型（OCR、Embedding、Image等）
                    if any(x in model_id.lower() for x in ["ocr", "embed", "image", "whisper", "tts"]):
                        continue
                    
                    # 获取使用量（可能有多种字段名）
                    stats = model.get("stats", {})
                    usage = stats.get("total_requests", 0) or stats.get("requests", 0) or 0
                    
                    free_models.append({
                        "id": model_id,
                        "name": model.get("name", model_id),
                        "context": model.get("context_length", 4096),
                        "usage": usage
                    })
            except Exception as e:
                logger.debug(f"Failed to parse model {model.get('id', 'unknown')}: {e}")
                continue
        
        # 按使用量排序（降序）
        free_models.sort(key=lambda x: x["usage"], reverse=True)
        
        logger.info(f"Found {len(free_models)} free models")
        return free_models
    
    @classmethod
    def list_top_free_models(cls, limit: int = 10, api_key: Optional[str] = None) -> List[Dict]:
        """列出最热门的免费模型（用于调试）"""
        models = cls._fetch_free_models(api_key)
        return models[:limit]
