from openai import AsyncOpenAI
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    """OpenAI API를 사용한 텍스트 요약 서비스"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def summarize_text(self, text: str, max_length: int = 150) -> Optional[str]:
        """텍스트를 요약합니다."""
        if not self.client:
            logger.error("OpenAI API key is not configured")
            return None
        
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided for summarization")
            return None
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"다음 텍스트를 {max_length}자 이내로 간결하게 요약해주세요. 핵심 내용만 포함하고 명확하고 이해하기 쉽게 작성해주세요."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                max_tokens=max_length + 50,  # 여유분 추가
                temperature=0.3,  # 일관성 있는 요약을 위해 낮은 온도 설정
                timeout=30  # 30초 타임아웃
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Text summarized successfully. Original length: {len(text)}, Summary length: {len(summary)}")
            return summary
            
        except Exception as e:
            logger.error(f"Error during text summarization: {e}")
            return None
    
    def is_configured(self) -> bool:
        """OpenAI API가 설정되어 있는지 확인합니다."""
        return self.client is not None