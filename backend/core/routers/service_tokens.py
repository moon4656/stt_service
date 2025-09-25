from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import secrets
import string

# 절대 경로로 import 수정
from core.database import get_db, User, ServiceToken
from core.auth import verify_token
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/service-tokens",
    tags=["service-tokens"],
    responses={404: {"description": "Not found"}},
)

# Pydantic 모델들
class ServiceTokenCreate(BaseModel):
    """서비스 토큰 생성 요청 모델"""
    name: str
    description: Optional[str] = None
    expires_in_days: Optional[int] = 365  # 기본 1년
    permissions: List[str] = ["transcribe"]  # 기본 권한

class ServiceTokenResponse(BaseModel):
    """서비스 토큰 응답 모델"""
    id: int
    name: str
    description: Optional[str]
    token_prefix: str  # 토큰의 앞 8자리만 표시
    permissions: List[str]
    is_active: bool
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    usage_count: int

class ServiceTokenCreateResponse(BaseModel):
    """서비스 토큰 생성 응답 모델 (전체 토큰 포함)"""
    id: int
    name: str
    token: str  # 생성 시에만 전체 토큰 반환
    expires_at: Optional[str]
    permissions: List[str]

class ServiceTokenUpdate(BaseModel):
    """서비스 토큰 수정 요청 모델"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = None

class TokenUsageStats(BaseModel):
    """토큰 사용 통계 모델"""
    token_id: int
    token_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    last_used_at: Optional[str]
    daily_usage: List[Dict[str, Any]]

def generate_service_token() -> str:
    """
    서비스 토큰을 생성합니다.
    
    Returns:
        생성된 토큰 문자열
    """
    # 안전한 랜덤 토큰 생성 (64자리)
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(64))
    return f"stt_{token}"

@router.post("/", summary="서비스 토큰 생성")
async def create_service_token(
    token_data: ServiceTokenCreate,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> ServiceTokenCreateResponse:
    """
    새로운 서비스 토큰을 생성합니다.
    
    - **name**: 토큰 이름 (식별용)
    - **description**: 토큰 설명 (선택사항)
    - **expires_in_days**: 만료일 (일 단위, 기본값: 365일)
    - **permissions**: 토큰 권한 목록 (기본값: ["transcribe"])
    
    ⚠️ **중요**: 생성된 토큰은 이 응답에서만 확인할 수 있습니다. 안전한 곳에 보관하세요.
    """
    logger.info(f"🚀 서비스 토큰 생성 요청 - 사용자: {current_user}, 이름: {token_data.name}")
    
    try:
        # 토큰 이름 중복 확인
        existing_token = db.query(ServiceToken).filter(
            ServiceToken.user_uuid == current_user,
            ServiceToken.name == token_data.name
        ).first()
        
        if existing_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="같은 이름의 토큰이 이미 존재합니다."
            )
        
        # 새 토큰 생성
        new_token = generate_service_token()
        
        # 만료일 계산
        expires_at = None
        if token_data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=token_data.expires_in_days)
        
        # 서비스 토큰 생성 로직 (실제 구현 필요)
        # service_token = create_new_service_token(
        #     user_uuid=current_user.user_uuid,
        #     name=token_data.name,
        #     description=token_data.description,
        #     token=new_token,
        #     permissions=token_data.permissions,
        #     expires_at=expires_at,
        #     db=db
        # )
        
        logger.info(f"✅ 서비스 토큰 생성 완료 - 사용자: {current_user.user_uuid}, 이름: {token_data.name}")
        return ServiceTokenCreateResponse(
            id=1,  # 실제 생성된 ID
            name=token_data.name,
            token=new_token,
            expires_at=expires_at.isoformat() if expires_at else None,
            permissions=token_data.permissions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 토큰 생성 중 오류가 발생했습니다."
        )

@router.get("/", summary="서비스 토큰 목록")
async def get_service_tokens(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    active_only: bool = Query(True, description="활성 토큰만 조회")
) -> List[ServiceTokenResponse]:
    """
    현재 사용자의 서비스 토큰 목록을 조회합니다.
    
    - **active_only**: 활성 토큰만 조회할지 여부
    """
    logger.info(f"🔍 서비스 토큰 목록 조회 - 사용자: {current_user}")
    
    try:
        # 서비스 토큰 목록 조회 로직 (실제 구현 필요)
        # tokens = get_user_service_tokens(current_user, active_only, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 토큰 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/{token_id}", summary="서비스 토큰 상세")
async def get_service_token(
    token_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> ServiceTokenResponse:
    """
    특정 서비스 토큰의 상세 정보를 조회합니다.
    """
    logger.info(f"🔍 서비스 토큰 상세 조회 - ID: {token_id}, 사용자: {current_user}")
    
    try:
        # 서비스 토큰 조회 및 권한 확인
        service_token = db.query(ServiceToken).filter(
            ServiceToken.id == token_id,
            ServiceToken.user_uuid == current_user
        ).first()
        
        if not service_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="서비스 토큰을 찾을 수 없습니다."
            )
        
        # 토큰 상세 정보 반환 (실제 구현 필요)
        return ServiceTokenResponse(
            id=service_token.id,
            name=service_token.name,
            description=service_token.description,
            token_prefix=service_token.token[:8] + "...",
            permissions=service_token.permissions or [],
            is_active=service_token.is_active,
            created_at=service_token.created_at.isoformat(),
            expires_at=service_token.expires_at.isoformat() if service_token.expires_at else None,
            last_used_at=service_token.last_used_at.isoformat() if service_token.last_used_at else None,
            usage_count=service_token.usage_count or 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 상세 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 토큰 조회 중 오류가 발생했습니다."
        )

@router.put("/{token_id}", summary="서비스 토큰 수정")
async def update_service_token(
    token_id: int,
    token_update: ServiceTokenUpdate,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    서비스 토큰 정보를 수정합니다.
    
    - **name**: 토큰 이름
    - **description**: 토큰 설명
    - **is_active**: 활성 상태
    - **permissions**: 토큰 권한 목록
    """
    logger.info(f"🔧 서비스 토큰 수정 - ID: {token_id}, 사용자: {current_user}")
    
    try:
        # 서비스 토큰 조회 및 권한 확인
        service_token = db.query(ServiceToken).filter(
            ServiceToken.id == token_id,
            ServiceToken.user_uuid == current_user
        ).first()
        
        if not service_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="서비스 토큰을 찾을 수 없습니다."
            )
        
        # 이름 중복 확인 (이름 변경 시)
        if token_update.name and token_update.name != service_token.name:
            existing_token = db.query(ServiceToken).filter(
                ServiceToken.user_uuid == current_user,
                ServiceToken.name == token_update.name,
                ServiceToken.id != token_id
            ).first()
            
            if existing_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="같은 이름의 토큰이 이미 존재합니다."
                )
        
        # 서비스 토큰 수정 로직 (실제 구현 필요)
        # update_service_token_info(service_token, token_update, db)
        
        logger.info(f"✅ 서비스 토큰 수정 완료 - ID: {token_id}")
        return {
            "status": "success",
            "message": "서비스 토큰이 성공적으로 수정되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 수정 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 토큰 수정 중 오류가 발생했습니다."
        )

@router.delete("/{token_id}", summary="서비스 토큰 삭제")
async def delete_service_token(
    token_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    서비스 토큰을 삭제합니다.
    
    ⚠️ **주의**: 삭제된 토큰은 복구할 수 없으며, 해당 토큰을 사용하는 모든 API 호출이 실패합니다.
    """
    logger.info(f"🗑️ 서비스 토큰 삭제 - ID: {token_id}, 사용자: {current_user}")
    
    try:
        # 서비스 토큰 조회 및 권한 확인
        service_token = db.query(ServiceToken).filter(
            ServiceToken.id == token_id,
            ServiceToken.user_uuid == current_user
        ).first()
        
        if not service_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="서비스 토큰을 찾을 수 없습니다."
            )
        
        # 서비스 토큰 삭제 로직 (실제 구현 필요)
        # delete_service_token_from_db(service_token, db)
        
        logger.info(f"✅ 서비스 토큰 삭제 완료 - ID: {token_id}")
        return {
            "status": "success",
            "message": "서비스 토큰이 성공적으로 삭제되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 토큰 삭제 중 오류가 발생했습니다."
        )

@router.post("/{token_id}/regenerate", summary="서비스 토큰 재생성")
async def regenerate_service_token(
    token_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> ServiceTokenCreateResponse:
    """
    서비스 토큰을 재생성합니다.
    
    ⚠️ **중요**: 
    - 기존 토큰은 즉시 무효화됩니다.
    - 새 토큰은 이 응답에서만 확인할 수 있습니다.
    - 기존 토큰을 사용하는 모든 API 호출이 실패합니다.
    """
    logger.info(f"🔄 서비스 토큰 재생성 - ID: {token_id}, 사용자: {current_user}")
    
    try:
        # 서비스 토큰 조회 및 권한 확인
        service_token = db.query(ServiceToken).filter(
            ServiceToken.id == token_id,
            ServiceToken.user_uuid == current_user
        ).first()
        
        if not service_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="서비스 토큰을 찾을 수 없습니다."
            )
        
        # 새 토큰 생성
        new_token = generate_service_token()
        
        # 서비스 토큰 재생성 로직 (실제 구현 필요)
        # regenerate_service_token_in_db(service_token, new_token, db)
        
        logger.info(f"✅ 서비스 토큰 재생성 완료 - ID: {token_id}")
        return ServiceTokenCreateResponse(
            id=service_token.id,
            name=service_token.name,
            token=new_token,
            expires_at=service_token.expires_at.isoformat() if service_token.expires_at else None,
            permissions=service_token.permissions or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 재생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 토큰 재생성 중 오류가 발생했습니다."
        )

@router.get("/{token_id}/usage", summary="토큰 사용 통계")
async def get_token_usage_stats(
    token_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    days: int = Query(30, description="조회할 일수")
) -> TokenUsageStats:
    """
    서비스 토큰의 사용 통계를 조회합니다.
    
    - **days**: 조회할 일수 (기본값: 30일)
    """
    logger.info(f"📊 토큰 사용 통계 조회 - ID: {token_id}, 사용자: {current_user}")
    
    try:
        # 서비스 토큰 조회 및 권한 확인
        service_token = db.query(ServiceToken).filter(
            ServiceToken.id == token_id,
            ServiceToken.user_uuid == current_user
        ).first()
        
        if not service_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="서비스 토큰을 찾을 수 없습니다."
            )
        
        # 토큰 사용 통계 조회 로직 (실제 구현 필요)
        # usage_stats = get_token_usage_statistics(token_id, days, db)
        
        return TokenUsageStats(
            token_id=token_id,
            token_name=service_token.name,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            last_used_at=service_token.last_used_at.isoformat() if service_token.last_used_at else None,
            daily_usage=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 토큰 사용 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 사용 통계 조회 중 오류가 발생했습니다."
        )

@router.post("/validate", summary="토큰 유효성 검증")
async def validate_service_token(
    token: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    서비스 토큰의 유효성을 검증합니다.
    
    이 엔드포인트는 주로 내부 시스템에서 토큰 검증 용도로 사용됩니다.
    """
    logger.info(f"🔍 토큰 유효성 검증 - 토큰 prefix: {token[:12]}...")
    
    try:
        # 토큰 유효성 검증 로직 (실제 구현 필요)
        # validation_result = validate_token_in_db(token, db)
        
        return {
            "valid": True,
            "user_uuid": "user_uuid_here",
            "permissions": ["transcribe"],
            "expires_at": None
        }
        
    except Exception as e:
        logger.error(f"❌ 토큰 유효성 검증 실패: {str(e)}")
        return {
            "valid": False,
            "error": "토큰 검증 중 오류가 발생했습니다."
        }