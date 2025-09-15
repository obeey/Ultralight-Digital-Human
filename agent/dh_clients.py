#!/usr/bin/env python3
"""
数字人客户端模块 - DeepSeek客户端和动作管理器
"""

import os
import logging
import random
import requests
import re
from typing import List, Tuple
from .dh_config import DigitalHumanConfig

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.error("未设置环境变量 DEEPSEEK_API_KEY，将使用备用话术")
        
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
    
    def _clean_text_for_tts(self, text: str) -> str:
        """清理文本，只保留标点符号，去除其他符号"""
        # 保留的标点符号：句号、逗号、问号、感叹号、顿号、分号、冒号
        allowed_punctuation = '。，？！、；：'
        
        # 移除所有非中文、非英文、非数字、非允许标点的字符
        # 包括：引号""''、括号()[]{}、星号*、井号#、at符号@、百分号%等
        cleaned_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s。，？！、；：]', '', text)
        
        # 清理多余的空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        # 记录清理前后的对比
        if text != cleaned_text:
            removed_chars = set(text) - set(cleaned_text)
            logger.info(f"文本清理完成，移除符号: {removed_chars}")
        
        return cleaned_text
    
    def generate_paragraph_script(self, product_info: str, paragraph_length: int = 200) -> str:
        """生成段落话术"""
        if not self.api_key:
            return self._get_fallback_paragraph(product_info)
        
        try:
            prompt = f"""
请为"{product_info}"生成一段直播带货话术，要求：
1. 长度约{paragraph_length}字符
2. 内容连贯，语言生动
3. 包含产品介绍、优惠信息、购买引导
4. 语气亲切自然，适合直播场景
5. 只使用基本标点符号（句号、逗号、问号、感叹号），不要使用其他符号
6. 不要使用引号、括号、星号、井号等特殊符号
7. 直接返回话术内容，不要其他说明

产品信息：{product_info}
"""
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 500
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # 使用专门的TTS文本清理函数
                cleaned_content = self._clean_text_for_tts(content)
                
                logger.info(f"DeepSeek生成段落话术成功，原始长度: {len(content)}字符，清理后长度: {len(cleaned_content)}字符")
                return cleaned_content
            else:
                logger.error(f"DeepSeek API请求失败: {response.status_code}")
                return self._get_fallback_paragraph(product_info)
                
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return self._get_fallback_paragraph(product_info)
    
    def _get_fallback_paragraph(self, product_info: str) -> str:
        """备用段落话术"""
        fallback_paragraphs = [
            f"宝宝们，{product_info}超值优惠来啦！现在下单立享折扣优惠，这个价格真的太划算了。数量有限，先到先得，喜欢的宝子赶紧点击小黄车下单吧。错过就没有了，这么好的机会不要犹豫了，立刻抢购！",
            f"各位宝宝注意了，{product_info}限时特价活动开始了！原价要几十块，现在只要这个价格，真的是白菜价了。质量绝对保证，大家放心购买，点击右下角小黄车立刻下单享受优惠价格。",
            f"宝宝们看过来，{product_info}今天特别优惠活动！这个产品平时很难买到，今天给大家争取到了最低价格。机会难得，数量真的不多了，喜欢的宝子抓紧时间下单，不要错过这个好机会。",
            f"亲爱的宝宝们，{product_info}超级划算的价格来了！这个质量这个价格真的找不到第二家了。现在下单还有额外优惠，赠品相送，点击小黄车马上抢购，库存不多售完即止。",
            f"宝子们，{product_info}爆款推荐！这个产品销量超高，好评如潮，现在活动价格真的太优惠了。平时买不到这个价格，今天给大家最大的优惠力度，赶紧下单抢购吧！"
        ]
        selected = random.choice(fallback_paragraphs)
        
        # 对备用话术也进行TTS清理
        cleaned_selected = self._clean_text_for_tts(selected)
        
        logger.info(f"使用备用段落话术，原始长度: {len(selected)}字符，清理后长度: {len(cleaned_selected)}字符")
        return cleaned_selected

class ActionManager:
    """智能动作管理器"""
    
    def __init__(self, total_images: int = 1178):
        self.total_images = total_images
        self.action_types = {
            'greeting': [(0, 150), (500, 650)],      # 问候动作
            'pointing': [(150, 300), (800, 950)],    # 指向动作  
            'excited': [(300, 450), (950, 1100)],    # 兴奋动作
            'explaining': [(450, 600), (1100, 1177)], # 解释动作
            'urging': [(600, 750), (200, 350)]       # 催促动作
        }
        
        self.keywords = {
            'greeting': ['宝宝', '大家', '各位', '亲爱', '朋友们', '宝子'],
            'pointing': ['点击', '小黄车', '链接', '右下角', '这里', '看这'],
            'excited': ['优惠', '特价', '限时', '抢购', '超值', '划算', '便宜'],
            'explaining': ['产品', '质量', '材质', '功能', '效果', '介绍'],
            'urging': ['赶紧', '快点', '马上', '立刻', '错过', '数量有限', '售完']
        }
    
    def analyze_text_action(self, text: str) -> str:
        """分析文本内容，返回最适合的动作类型"""
        action_scores = {action_type: 0 for action_type in self.action_types}
        
        # 计算每种动作类型的匹配分数
        for action_type, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in text:
                    action_scores[action_type] += 1
        
        # 选择得分最高的动作类型
        best_action = max(action_scores, key=action_scores.get)
        
        # 如果没有匹配的关键词，随机选择
        if action_scores[best_action] == 0:
            best_action = random.choice(list(self.action_types.keys()))
        
        logger.info(f"文本'{text[:20]}...' 匹配动作类型: {best_action}")
        return best_action
    
    def get_action_range(self, action_type: str) -> Tuple[int, int]:
        """获取动作类型对应的图片范围"""
        ranges = self.action_types.get(action_type, [(0, 100)])
        selected_range = random.choice(ranges)
        logger.info(f"选择动作范围: {selected_range[0]}-{selected_range[1]} ({action_type})")
        return selected_range