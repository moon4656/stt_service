from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
from datetime import datetime

from core.database import get_db
from core.auth import verify_token, verify_api_key_dependency, TokenManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tokens",
    tags=["토큰"]
)

class TokenCreate(BaseModel):
    token_id: str
    description: Optional[str] = ""

class TokenRevoke(BaseModel):
    api_key_hash: str

@router.post("/{token_id}", summary="API 키 발행")
def create_token(
    token_id: str, 
    description: Optional[str] = "", 
    current_user: str = Depends(verify_token), 
    db: Session = Depends(get_db)
):
    """
    사용자별 API 키를 발행합니다.
    
    - **token_id**: 토큰 식별자 (사용자별 고유)
    - **description**: 토큰 설명 (선택사항)
    
    Returns:
        발행된 API 키 정보
    """
    try:
        logger.info(f"🔑 API 키 발행 요청 - user: {current_user}, token_id: {token_id}")

        # TokenManager를 사용하여 API 키 생성
        result = TokenManager.generate_api_key(
            user_uuid=current_user,
            token_id=token_id,
            description=description,
            db=db
        )
        
        logger.info(f"✅ API 키 발행 성공 - token_id: {token_id}")
        
        return {
            "message": "API 키가 성공적으로 발행되었습니다.",
            "token_id": result["token_id"],
            "api_key": result["api_key"],
            "description": result["description"],
            "created_at": result["created_at"],
            "is_active": result["is_active"]
        }
        
    except ValueError as e:
        logger.warning(f"⚠️ API 키 발행 실패 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ API 키 발행 오류 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 키 발행 중 오류가 발생했습니다."
        )

@router.get("/verify", summary="API 키 검증")
def verify_token_endpoint(
    current_user: str = Depends(verify_api_key_dependency), 
    db: Session = Depends(get_db)
):
    """
    API 키의 유효성을 검증합니다.
    
    Returns:
        API 키 검증 결과
    """
    try:
        logger.info(f"🔍 API 키 검증 요청 - user: {current_user}")
        
        return {
            "message": "API 키가 유효합니다.",
            "user_uuid": current_user,
            "verified_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ API 키 검증 오류 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 키 검증 중 오류가 발생했습니다."
        )

@router.get("/", summary="사용자 토큰 목록 조회")
def get_user_tokens(    
    current_user: str = Depends(verify_token), 
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    현재 사용자의 모든 토큰 목록을 조회합니다.
    
    Args:
        is_active: 토큰 활성 상태 필터 (None=전체, True=활성, False=비활성)
        
    Returns:
        사용자의 토큰 목록
    """
    try:
        logger.info(f"📋 토큰 목록 조회 요청 - user: {current_user}, is_active: {is_active}")
        
        tokens = TokenManager.get_user_tokens(current_user, db, is_active)  
        
        logger.info(f"✅ 토큰 목록 조회 성공 - 토큰 수: {len(tokens)}")
        
        return {
            "status": "success",
            "message": "토큰 목록 조회 성공",
            "tokens": tokens,
            "total_count": len(tokens)
        }
        
    except Exception as e:
        logger.error(f"❌ 토큰 목록 조회 오류 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 목록 조회 중 오류가 발생했습니다."
        )

@router.post("/revoke", summary="API 키 비활성화")
def revoke_token(
    revoke_request: TokenRevoke, 
    current_user: str = Depends(verify_token), 
    db: Session = Depends(get_db)
):
    """
    API 키를 비활성화합니다.
    
    - **api_key_hash**: 비활성화할 API 키의 해시값
    
    Returns:
        비활성화 결과
    """
    try:
        logger.info(f"🔒 API 키 비활성화 요청 - user: {current_user}")
        
        success = TokenManager.revoke_api_key(
            api_key_hash=revoke_request.api_key_hash,
            user_uuid=current_user,
            db=db
        )
        
        if success:
            logger.info(f"✅ API 키 비활성화 성공")
            return {
                "status": "success",
                "message": "API 키가 성공적으로 비활성화되었습니다.",
                "api_key_hash": revoke_request.api_key_hash
            }
        else:
            logger.warning(f"⚠️ API 키 비활성화 실패 - 키를 찾을 수 없음")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 API 키를 찾을 수 없습니다."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API 키 비활성화 오류 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 키 비활성화 중 오류가 발생했습니다."
        )

@router.get("/history", summary="토큰 사용 내역 조회")
def get_token_history(
    limit: int = 50, 
    current_user: str = Depends(verify_token), 
    db: Session = Depends(get_db)
):
    """
    토큰 사용 내역을 조회합니다.
    
    - **limit**: 조회할 내역 수 (기본값: 50)
    
    Returns:
        토큰 사용 내역
    """
    try:
        logger.info(f"📊 토큰 사용 내역 조회 요청 - user: {current_user}, limit: {limit}")
        
        history = TokenManager.get_token_history(current_user, limit, db)
        
        logger.info(f"✅ 토큰 사용 내역 조회 성공 - 내역 수: {len(history)}")
        
        return {
            "message": "토큰 사용 내역 조회 성공",
            "history": history,
            "total_count": len(history)
        }
        
    except Exception as e:
        logger.error(f"❌ 토큰 사용 내역 조회 오류 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 사용 내역 조회 중 오류가 발생했습니다."
        )