import requests
from typing import Dict, List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging

class ChatManager:
    def __init__(self, api_url: str, api_key: str, model: str, max_history: int = 10):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.conversation_history = []
        self.max_history = max_history * 2  # 因为每次对话包含问题和回答两条记录
        
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 初始化文本向量化器
        self.vectorizer = TfidfVectorizer(
            token_pattern=r'(?u)\b\w+\b',  # 支持中文分词
            max_features=5000,  # 限制特征数量
            stop_words=None  # 保留所有词，包括停用词
        )
        
    def find_relevant_context(self, query: str, chunks: List[str], top_k: int = 3) -> str:
        """找到与问题最相关的文档片段"""
        try:
            # 将所有文本向量化
            all_texts = chunks + [query]
            vectors = self.vectorizer.fit_transform(all_texts)
            
            # 计算余弦相似度
            similarities = (vectors[:-1] @ vectors[-1].T).toarray().flatten()
            
            # 获取最相关的片段
            top_indices = np.argsort(similarities)[-top_k:][::-1]  # 反转顺序，最相关的在前
            relevant_chunks = [chunks[i] for i in top_indices]
            
            # 记录日志
            self.logger.info(f"找到 {top_k} 个相关片段，相似度：{similarities[top_indices]}")
            
            return "\n\n".join(relevant_chunks)
            
        except Exception as e:
            self.logger.error(f"查找相关内容时出错: {str(e)}", exc_info=True)
            raise
        
    def _trim_history(self):
        """保持对话历史在限定长度内"""
        if len(self.conversation_history) > self.max_history:
            # 保留最近的对话
            self.conversation_history = self.conversation_history[-self.max_history:]
            self.logger.info(f"对话历史已截断至 {self.max_history} 条")
            
    def generate_summary(self, context: str) -> str:
        """生成学习内容总结"""
        try:
            summary_prompt = self.get_summary_prompt(context)
            return self.send_message(summary_prompt, context)
        except Exception as e:
            self.logger.error(f"生成总结时出错: {str(e)}", exc_info=True)
            raise Exception(f"生成总结失败: {str(e)}")
            
    def send_message(self, message: str, context: str = "") -> str:
        """发送消息给AI并获取回复"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 根据不同场景选择不同的提示词
            if message.startswith("请总结"):
                system_prompt = self.get_summary_prompt(context)
            elif message.startswith("复习建议"):
                system_prompt = self.get_review_prompt(context)
            else:
                system_prompt = self.get_base_prompt(context)
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *self.conversation_history,
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7,  # 添加温度参数，控制回答的创造性
                "max_tokens": 4000,  # 限制回答长度
                "top_p": 0.95,  # 控制输出的多样性
            }
            
            self.logger.info(f"发送请求到 API，消息长度：{len(message)}")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            ai_response = response.json()["choices"][0]["message"]["content"]
            self.logger.info(f"收到 API 响应，回复长度：{len(ai_response)}")
            
            # 在添加新对话前清理历史
            self._trim_history()
            
            # 添加新对话
            self.conversation_history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": ai_response}
            ])
            
            return ai_response
            
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请稍后重试"
            self.logger.error(error_msg)
            raise Exception(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API 请求失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"发送消息时出错: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
            
    def get_review_prompt(self, context: str) -> str:
        """生成复习建议的提示词"""
        return f"""请基于以下内容，生成有效的复习建议。

学习内容：
{context}

请从以下几个方面提供建议：
1. 重点复习内容提示
2. 理解检查问题
3. 应用练习建议
4. 知识扩展方向
5. 常见错误提醒

建议要具体、可操作，并注意：
1. 设置适当的复习难度
2. 联系实际应用场景
3. 加入互动性检验
4. 提供思考方向
5. 建议多角度理解"""

    def get_base_prompt(self, context: str) -> str:
        """生成基础对话的提示词"""
        return f"""你是一位专业的学习助手，擅长通过对话的方式帮助用户理解和掌握知识。请基于以下文档内容，以及你的专业知识来辅助用户学习。

文档内容：
{context}

指导原则：
1. 采用苏格拉底式问答方法，通过提问引导用户思考
2. 解释要由浅入深，循序渐进
3. 多使用类比和实例来解释抽象概念
4. 适时总结和回顾重要知识点
5. 鼓励用户提出问题和思考

回答要求：
1. 回答要清晰、准确、易懂
2. 适当使用分点或分段来组织内容
3. 重要概念要突出显示
4. 必要时提供额外的相关知识
5. 保持友好和耐心的语气

如果用户的问题超出文档范围，可以基于你的知识适度扩展，但要明确指出这是补充内容。"""

    def get_summary_prompt(self, context: str) -> str:
        return """请对《贫穷的本质》这本书进行全面而深入的总结。请使用严格的markdown格式：

# 《贫穷的本质》

## 作者背景
- 阿比吉特·班纳吉：麻省理工学院经济学教授，2019年诺贝尔经济学奖得主
- 埃斯特·迪弗洛：麻省理工学院经济学教授，2019年诺贝尔经济学奖得主
- 研究领域：发展经济学、贫困问题、实验经济学
- 学术贡献：将实验方法引入发展经济学研究

## 研究方法
### 随机对照试验（RCT）
- 方法原理与应用
- 实验设计特点
- 数据收集过程
- 结果分析方法

### 实地调研
- 调研方法设计
- 样本选择策略
- 数据质量控制
- 信息收集技术

### 跨学科方法
- 经济学分析
- 心理学视角
- 社会学观点
- 人类学方法

## 核心论点
### 贫困的多维性
- 收入维度
- 机会维度
- 能力维度
- 社会维度

### 贫困陷阱机制
- 营养与健康陷阱
- 教育与技能陷阱
- 信贷与资本陷阱
- 信息与认知陷阱

### 行为经济学视角
- 决策环境影响
- 认知资源限制
- 时间偏好问题
- 风险态度差异

## 研究发现
### 贫困者的决策逻辑
- 资源分配策略
- 风险管理方式
- 时间偏好选择
- 机会成本考量

### 制度性障碍
- 市场失灵问题
- 政府服务缺失
- 信息不对称
- 社会排斥现象

### 干预效果分析
- 教育干预结果
- 健康项目影响
- 小额信贷效果
- 技术推广成效

## 政策建议
### 微观层面
- 行为干预设计
- 激励机制优化
- 信息获取改善
- 能力建设支持

### 宏观层面
- 制度环境优化
- 市场功能完善
- 公共服务提升
- 社会保护体系

### 创新方案
- 技术应用建议
- 金融产品创新
- 服务递送改进
- 评估体系设计

## 理论贡献
### 理论创新
- 贫困理论突破
- 方法论创新
- 分析框架拓展
- 跨学科整合

### 实践指导
- 项目设计指导
- 实施策略建议
- 评估方法创新
- 推广经验总结

## 批判性思考
### 研究局限
- 方法论局限
- 样本代表性
- 结论推广性
- 长期效果评估

### 未来研究方向
- 理论深化方向
- 方法改进空间
- 新议题探索
- 跨文化研究

## 现实意义
### 对发展中国家的启示
- 政策制定参考
- 项目设计借鉴
- 实施策略启发
- 评估方法借鉴

### 对扶贫实践的指导
- 项目设计原则
- 实施路径优化
- 效果评估方法
- 可持续性建议

### 对国际发展的影响
- 发展理论贡献
- 实践经验启示
- 国际合作建议
- 援助方式创新

请确保：
1. 严格遵循markdown语法
2. 使用#、##、###标记标题层级
3. 使用-标记列表项
4. 保持层级结构清晰
5. 内容准确完整
6. 逻辑连贯
7. 便于转换为思维导图

如果某些内容在文本中未明确提及，请基于上下文和专业知识合理推断。输出必须严格遵循markdown格式。"""