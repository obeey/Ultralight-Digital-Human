#!/usr/bin/env python3
"""
数字人客户端模块 - DeepSeek客户端和动作管理器
"""

import os
import logging
import random
import requests
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
5. 不要使用标点符号分段，让语音更连贯
6. 直接返回话术内容，不要其他说明

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
                # 清理可能的引号和多余空格
                content = content.replace('"', '').replace("'", '').strip()
                logger.info(f"DeepSeek生成段落话术成功，长度: {len(content)}字符")
                return content
            else:
                logger.error(f"DeepSeek API请求失败: {response.status_code}")
                return self._get_fallback_paragraph(product_info)
                
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return self._get_fallback_paragraph(product_info)
    
    def _get_fallback_paragraph(self, product_info: str) -> str:
        """备用段落话术"""
        fallback_paragraphs = [
            f"宝宝们{product_info}超值优惠来啦现在下单立享折扣优惠这个价格真的太划算了数量有限先到先得喜欢的宝子赶紧点击小黄车下单吧错过就没有了这么好的机会不要犹豫了立刻抢购",
            f"各位宝宝注意了{product_info}限时特价活动开始了原价要几十块现在只要这个价格真的是白菜价了质量绝对保证大家放心购买点击右下角小黄车立刻下单享受优惠价格",
            f"宝宝们看过来{product_info}今天特别优惠活动这个产品平时很难买到今天给大家争取到了最低价格机会难得数量真的不多了喜欢的宝子抓紧时间下单不要错过这个好机会",
            f"亲爱的宝宝们{product_info}超级划算的价格来了这个质量这个价格真的找不到第二家了现在下单还有额外优惠赠品相送点击小黄车马上抢购库存不多售完即止",
            f"宝子们{product_info}爆款推荐这个产品销量超高好评如潮现在活动价格真的太优惠了平时买不到这个价格今天给大家最大的优惠力度赶紧下单抢购吧"
        ]
        selected = random.choice(fallback_paragraphs)
        logger.info(f"使用备用段落话术，长度: {len(selected)}字符")
        return selected

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