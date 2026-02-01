
import json
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from sqlmodel import Session, select

from backend.core.config import settings
from backend.models import User, UserProfile
from backend.services.rag_service import rag_service
from backend.core.cache import CacheManager  # Task 110: Redis Cache

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL or "https://api.moonshot.cn/v1"
        self.model = settings.OPENAI_MODEL or "moonshot-v1-8k"
        
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None
            logger.warning("ChatService: OPENAI_API_KEY missing. Chat response will be degraded.")

    async def chat(self, user: User, query: str, session: Session, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Process user chat with RAG context and User Profile.
        Task 110: 添加 Redis 缓存支持
        Task 111: 支持 force_refresh 强制刷新
        """
        # Task 110: 生成缓存 Key (基于用户ID和问题)
        cache_key = CacheManager.generate_key(
            "chat_response",
            str(user.id),
            query.strip().lower()  # 标准化问题
        )
        
        # Task 111: 只有不强制刷新时才查缓存
        if not force_refresh:
            cached_data = await CacheManager.get(cache_key)
            if cached_data:
                print(f"⚡ Cache Hit for query: {query[:50]}...")
                logger.info(f"⚡ Cache Hit: Chat [{cache_key[:20]}...]")
                return {
                    "reply": cached_data.get("reply", ""),
                    "sources": cached_data.get("sources", []),
                    "source": "cache"  # 标记来源
                }
        else:
            print(f"🔄 Force Refresh: Bypassing cache for query: {query[:50]}...")
        
        if not self.client:
            return {
                "reply": "I'm sorry, my brain (LLM) is not connected. Please check configuration.",
                "sources": []
            }

        # 1. Fetch User Profile & Health Context
        profile_summary = self._get_user_context(user, session)
        
        # 2. Retrieve RAG Context
        # Search for relevant medical guidelines
        rag_context = rag_service.search_context(query, k=3)
        sources = []
        if rag_context:
            # Extract source names for citation
            # format: [Ref X - filename]: content
            # Quick parse to get unique filenames
            import re
            matches = re.findall(r"Ref \d+ - (.*?)]", rag_context)
            sources = list(set(matches))

        # 3. Construct System Prompt
        system_prompt = (
            "你是 Dr. AI，一位基于循证医学的专业健康顾问。\n"
            "你的任务是根据提供的【参考资料】和【用户画像】来回答用户的健康问题。\n\n"
            "核心原则：\n"
            "1. **结合画像**：必须考虑到用户的年龄、性别、风险标签及异常指标。例如，如果用户有高血压，建议中应包含高血压相关的注意事项。\n"
            "2. **循证医学**：优先依据【参考资料】中的内容。如果资料中没有直接答案，请基于通用医学常识谨慎回答，并声明仅供参考。\n"
            "3. **专业且亲切**：以医生口吻回答，既要严谨又要易懂。\n"
            "4. **安全第一**：严禁开具处方药，遇到急重症请建议立即就医。\n"
        )

        user_prompt = (
            f"【用户画像】\n{profile_summary}\n\n"
            f"【参考资料 (RAG)】\n{rag_context if rag_context else '暂无直接相关指南资料。'}\n\n"
            f"【用户问题】\n{query}"
        )

        # 4. Call LLM
        try:
            # Task 86: Removed temperature, max_tokens for Kimi k2.5 compatibility
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            reply_text = response.choices[0].message.content
            
            # Task 86: Clean up <think> tags if present (Kimi reasoning output)
            import re
            reply_text = re.sub(r'<think>.*?</think>', '', reply_text, flags=re.DOTALL).strip()
            
            result = {
                "reply": reply_text,
                "sources": sources
            }
            
            # Task 110: 写入缓存 (TTL=1小时)
            await CacheManager.set(cache_key, result, ttl=3600)
            logger.info(f"📝 Cached Chat Response [{cache_key[:20]}...] for 1h")
            
            return result
            
        except Exception as e:
            logger.error(f"Chat LLM Error: {e}")
            return {
                "reply": "抱歉，我暂时无法思考（服务连接失败），请稍后再试。",
                "sources": []
            }

    def _get_user_context(self, user: User, session: Session) -> str:
        """
        Extract key health metrics and risks from profile.
        """
        if not user.profile:
            return f"用户ID: {user.username}, 暂无详细体检档案。"
            
        p = user.profile
        
        # Extract Risks (if any)
        # Assuming database has some risk fields or we parse from JSON
        risks = []
        if p.risk_history:
            try:
                # Assuming risk_history is a JSON string of historical reports
                # We might just grab the latest prediction or just use raw metrics
                pass
            except:
                pass
        
        # Identify abnormal metrics (Simple Rules for Context)
        abnormals = []
        if p.BMI and p.BMI > 24: abnormals.append(f"BMI偏高({p.BMI})")
        if p.SBP and p.SBP > 140: abnormals.append(f"收缩压偏高({p.SBP})")
        if p.Glucose_Fasting and p.Glucose_Fasting > 6.1: abnormals.append(f"空腹血糖偏高({p.Glucose_Fasting})")
        # if p.recomm_tags: abnormals.append(f"标签:{p.recomm_tags}")

        # Basic Info
        age = p.Age if p.Age else "未知"
        gender = "男" if p.Gender == 1 else "女" if p.Gender == 2 else "未知"
        
        context_str = (
            f"- 基本信息: {age}岁, {gender}\n"
            f"- 关键风险/异常: {', '.join(abnormals) if abnormals else '无明显异常记录'}\n"
            f"- 诊断历史: {p.risk_history[:100] if p.risk_history else '无'}"
        )
        return context_str

# Singleton
chat_service = ChatService()
