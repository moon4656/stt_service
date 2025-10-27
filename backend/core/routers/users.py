from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

# 로컬 임포트
from core.database import get_db, User
from core.auth import verify_token
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# Pydantic 모델들
class UserCreate(BaseModel):
    """사용자 생성 요청 모델"""
    email: EmailStr
    password: str
    user_type: str = "free"

class UserProfile(BaseModel):
    """사용자 프로필 응답 모델"""
    user_uuid: str
    email: str
    user_type: str
    created_at: str
    is_active: bool

class UserSettings(BaseModel):
    """사용자 설정 모델"""
    email_notifications: bool = True
    language: str = "ko"
    timezone: str = "Asia/Seoul"

@router.post("/", summary="사용자 생성")
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    새로운 사용자를 생성합니다.
    
    - **email**: 사용자 이메일 주소
    - **password**: 사용자 비밀번호
    - **user_type**: 사용자 타입 (free, premium, enterprise)
    """
    logger.info(f"🚀 사용자 생성 요청 - 이메일: {user_data.email}")
    
    try:
        # 이메일 중복 확인
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            logger.warning(f"⚠️ 이메일 중복 - {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 이메일 주소입니다."
            )
        
        # 사용자 생성 로직 (실제 구현 필요)
        # new_user = create_new_user(user_data, db)
        
        logger.info(f"✅ 사용자 생성 완료 - 이메일: {user_data.email}")
        return {
            "status": "success",
            "message": "사용자가 성공적으로 생성되었습니다.",
            "user_uuid": "generated_uuid"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 생성 중 오류가 발생했습니다."
        )

@router.get("/profile", summary="사용자 프로필 조회")
async def get_user_profile(
    current_user: str = Depends(verify_token)
) -> UserProfile:
    """
    현재 로그인한 사용자의 프로필 정보를 조회합니다.
    """
    logger.info(f"🔍 사용자 프로필 조회 - UUID: {current_user.user_uuid}")
    
    try:
        return UserProfile(
            user_uuid=current_user.user_uuid,
            email=current_user.email,
            user_type=current_user.user_type,
            created_at=current_user.created_at.isoformat(),
            is_active=current_user.is_active
        )
        
    except Exception as e:
        logger.error(f"❌ 프로필 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 조회 중 오류가 발생했습니다."
        )

@router.get("/settings", summary="사용자 설정 조회")
async def get_user_settings(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> UserSettings:
    """
    현재 로그인한 사용자의 설정을 조회합니다.
    """
    logger.info(f"⚙️ 사용자 설정 조회 - UUID: {current_user.user_uuid}")
    
    try:
        # 사용자 설정 조회 로직 (실제 구현 필요)
        # settings = get_user_settings_from_db(current_user.user_uuid, db)
        
        return UserSettings(
            email_notifications=True,
            language="ko",
            timezone="Asia/Seoul"
        )
        
    except Exception as e:
        logger.error(f"❌ 설정 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="설정 조회 중 오류가 발생했습니다."
        )

@router.put("/settings", summary="사용자 설정 업데이트")
async def update_user_settings(
    settings: UserSettings,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    현재 로그인한 사용자의 설정을 업데이트합니다.
    
    - **email_notifications**: 이메일 알림 수신 여부
    - **language**: 언어 설정
    - **timezone**: 시간대 설정
    """
    logger.info(f"🔧 사용자 설정 업데이트 - UUID: {current_user.user_uuid}")
    
    try:
        # 사용자 설정 업데이트 로직 (실제 구현 필요)
        # update_user_settings_in_db(current_user.user_uuid, settings, db)
        
        logger.info(f"✅ 설정 업데이트 완료 - UUID: {current_user.user_uuid}")
        return {
            "status": "success",
            "message": "설정이 성공적으로 업데이트되었습니다."
        }
        
    except Exception as e:
        logger.error(f"❌ 설정 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="설정 업데이트 중 오류가 발생했습니다."
        )