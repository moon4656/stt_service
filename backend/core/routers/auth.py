from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional

from core.database import get_db
from core.auth import (
    create_access_token,
    authenticate_user,
    verify_token,
    hash_password,
    verify_password
)

router = APIRouter(
    prefix="/auth",
    tags=["인증"]
)

class LoginRequest(BaseModel):
    email: str
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "test_01@sample.com",
                "password": "test"
            }
        }
    )

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/login", summary="사용자 로그인")
def login(login_request: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    사용자 로그인을 처리합니다.
    
    - **email**: 사용자 이메일 주소
    - **password**: 사용자 비밀번호
    
    성공 시 JWT 액세스 토큰을 반환합니다.
    """
    try:
        # 사용자 인증
        user_info = authenticate_user(login_request.email, login_request.password, db)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="메일 또는 비밀번호를 확인해주세요.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 에러 응답 처리 (계정 잠금 등)
        if isinstance(user_info, dict) and "error" in user_info:
            if user_info["error"] == "account_locked":
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=user_info["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=user_info["message"]
                )
        
        # JWT 토큰 생성
        access_token = create_access_token(
            data={"sub": user_info["user_uuid"], "email": user_info["email"]}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_info": {
                "user_uuid": user_info["user_uuid"],
                "email": user_info["email"],
                "name": user_info["name"],
                "user_type": user_info["user_type"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
        )

@router.put("/change-password", summary="패스워드 변경")
def change_password(
    password_request: PasswordChangeRequest, 
    current_user: str = Depends(verify_token), 
    db: Session = Depends(get_db)
):
    # 기존 패스워드 변경 로직 이동
    pass

@router.post("/unlock-account", summary="계정 잠금 해제")
def unlock_account(
    email: str,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # 기존 계정 잠금 해제 로직 이동
    pass