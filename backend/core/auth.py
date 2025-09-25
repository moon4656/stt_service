import jwt
from datetime import datetime, timedelta
import secrets
import hashlib
from typing import Optional, Dict, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import os
from sqlalchemy.orm import Session
# 절대 경로로 import 수정
from core.database import User, APIToken, get_db
import bcrypt

import logging
logger = logging.getLogger(__name__)

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# 보안 스키마
security = HTTPBearer()

# 메모리 기반 사용자 및 토큰 저장소 (실제 환경에서는 데이터베이스 사용)
users_db = {}
tokens_db = {}
token_history_db = []

# 패스워드 해시화 함수들
def hash_password(password: str) -> str:
    """패스워드를 bcrypt로 해시화"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """패스워드 검증"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

class TokenManager:
    @staticmethod
    def generate_api_key(user_uuid: str, token_id: str, description: str = "", db: Session = None) -> Dict:
        """사용자별 API 키 생성"""
        if db is None:
            # 기존 메모리 기반 로직 유지 (하위 호환성)
            for existing_token in tokens_db.values():
                if existing_token.get("token_id") == token_id and existing_token["user_uuid"] == user_uuid:
                    raise ValueError(f"Token ID '{token_id}' already exists for this user")
        else:
            # 데이터베이스에서 중복 확인
            existing_token = db.query(APIToken).filter(
                APIToken.user_uuid == user_uuid,
                APIToken.token_id == token_id,
                APIToken.is_active == True
            ).first()
            if existing_token:
                raise ValueError(f"Token ID '{token_id}' already exists for this user")
        
        # API 키 생성 (32바이트 랜덤 문자열)
        api_key = secrets.token_urlsafe(32)
        
        # API 키 해시 (저장용)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 현재 시간
        created_at = datetime.utcnow()
        
        if db is not None:
            # 데이터베이스에 토큰 저장
            db_token = APIToken(
                user_uuid=user_uuid,
                token_id=token_id,
                token_key=api_key_hash,
                api_key=api_key,  # 신규 컬럼에 평문 API 키 저장
                token_name=description,
                is_active=True,
                created_at=created_at
            )
            db.add(db_token)
            db.commit()
            db.refresh(db_token)
        
        # 메모리에도 저장 (기존 로직과의 호환성)
        token_info = {
            "api_key_hash": api_key_hash,
            "token_id": token_id,
            "user_uuid": user_uuid,
            "description": description,
            "created_at": created_at.isoformat(),
            "is_active": True,
            "usage_count": 0,
            "last_used": None
        }
        
        tokens_db[api_key_hash] = token_info
        
        # 히스토리 저장
        token_history_db.append({
            "action": "created",
            "api_key_hash": api_key_hash,
            "token_id": token_id,
            "user_uuid": user_uuid,
            "timestamp": created_at.isoformat(),
            "description": description
        })
        
        return {
            "api_key": api_key,
            "api_key_hash": api_key_hash,
            "token_id": token_id,
            "user_uuid": user_uuid,
            "description": description,
            "created_at": created_at.isoformat(),
            "is_active": True
        }
    
    @staticmethod
    def verify_api_key(api_key: str, db: Session = None) -> Optional[Dict]:
        """API 키 검증 (데이터베이스 우선)"""
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if db is not None:
            # 데이터베이스에서 토큰 검증
            db_token = db.query(APIToken).filter(
                APIToken.token_key == api_key_hash,
                APIToken.is_active == True
            ).first()
            
            if db_token:
                # 마지막 사용 시간 업데이트
                db_token.last_used_at = datetime.utcnow()
                db.commit()
                
                return {
                    "user_uuid": db_token.user_uuid,
                    "token_id": db_token.token_id,
                    "token_name": db_token.token_name,
                    "created_at": db_token.created_at.isoformat(),
                    "last_used_at": db_token.last_used_at.isoformat() if db_token.last_used_at else None,
                    "is_active": db_token.is_active
                }
            return None
        
        # 메모리 기반 검증 (하위 호환성)
        token_info = tokens_db.get(api_key_hash)
        if not token_info or not token_info["is_active"]:
            return None
        
        # 사용 횟수 증가 및 마지막 사용 시간 업데이트
        token_info["usage_count"] += 1
        token_info["last_used"] = datetime.utcnow().isoformat()
        
        return {
            "user_uuid": token_info["user_uuid"],
            "token_id": token_info["token_id"],
            "description": token_info["description"],
            "created_at": token_info["created_at"],
            "last_used": token_info["last_used"],
            "is_active": token_info["is_active"]
        }
    
    @staticmethod
    def get_user_tokens(user_uuid: str, db: Session = None, is_active: Optional[bool] = None) -> List[Dict]:
        """사용자의 모든 토큰 조회"""
        tokens = []
        logger.info(f"📋 ㅁㅁㅁㅁㅁㅁㅁㅁㅁ토큰 목록 조회 요청 - user: {user_uuid}, is_active: {is_active}, db : {db}")
        if db is not None:
            # 데이터베이스에서 토큰 조회
            db_tokens = db.query(APIToken).filter(
                APIToken.user_uuid == user_uuid,
                APIToken.is_active == is_active
            ).order_by(APIToken.created_at.desc()).all()
            
            for token in db_tokens:
                tokens.append({
                    "token_id": token.token_id,
                    "token_name": token.token_name,
                    "description": token.description or token.token_name,  # description 필드 추가
                    "token_key": token.token_key,  # 프론트엔드에서 필요한 필드
                    "is_active": token.is_active,
                    "api_key": token.api_key,  # 프론트엔드에서 필요한 필드
                    "created_at": token.created_at.isoformat(),
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                })
        
        # 메모리에서도 조회 (기존 로직과의 호환성)
        for token_hash, token_info in tokens_db.items():
            if token_info["user_uuid"] == user_uuid and token_info["is_active"]:
                # 데이터베이스에서 이미 조회된 토큰과 중복 방지
                if db is None or not any(t["token_id"] == token_info["token_id"] for t in tokens):
                    tokens.append({
                        "token_id": token_info["token_id"],
                        "token_name": token_info["description"],
                        "created_at": token_info["created_at"],
                        "last_used_at": token_info["last_used"],
                        "is_active": token_info["is_active"]
                    })
        
        return tokens
    
    @staticmethod
    def revoke_api_key(api_key_hash: str, user_uuid: str, db: Session = None) -> bool:
        """API 키 비활성화"""
        if db is not None:
            # 데이터베이스에서 토큰 비활성화
            db_token = db.query(APIToken).filter(
                APIToken.api_key == api_key_hash,
                APIToken.user_uuid == user_uuid,
                APIToken.is_active == True
            ).first()
            
            if db_token:
                db_token.is_active = False
                db.commit()
                
                # 히스토리 저장
                token_history_db.append({
                    "action": "revoked",
                    "api_key_hash": api_key_hash,
                    "user_uuid": user_uuid,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return True
            return False
        
        # 메모리 기반 비활성화 (하위 호환성)
        token_info = tokens_db.get(api_key_hash)
        if not token_info or token_info["user_uuid"] != user_uuid:
            return False
        
        token_info["is_active"] = False
        token_info["revoked_at"] = datetime.utcnow().isoformat()
        
        # 히스토리 저장
        token_history_db.append({
            "action": "revoked",
            "api_key_hash": api_key_hash,
            "user_uuid": user_uuid,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    @staticmethod
    def get_token_history(user_uuid: str, limit: int = 50, db: Session = None) -> List[Dict]:
        """사용자의 토큰 사용 내역 조회"""
        user_history = [
            history for history in token_history_db 
            if history["user_uuid"] == user_uuid
        ]
        
        # 최신 순으로 정렬
        user_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return user_history[:limit]

def authenticate_user(email: str, password: str, db: Session = None) -> Optional[Dict]:
    """사용자 인증 (패스워드 검증)"""
    print(f"🔍 authenticate_user 호출 - email: {email}")
    close_db = False
    if db is None:
        db = next(get_db())
        close_db = True
    
    try:
        # 데이터베이스에서 사용자 조회
        user = db.query(User).filter(User.email == email).first()
        print(f"🔍 사용자 조회 결과: {user is not None}")
        
        if user:
            print(f"🔍 사용자 정보: email={user.email}, is_locked={user.is_locked}, failed_attempts={user.failed_login_attempts}")
        
        if not user:
            print(f"🔍 사용자를 찾을 수 없음: {email}")
            return None
        
        # 계정 잠금 상태 확인 (None 처리 포함)
        if user.is_locked is True:
            # 잠금 해제 조건 확인 (예: 30분 후 자동 해제)
            if user.locked_at and datetime.now() - user.locked_at > timedelta(minutes=30):
                # 잠금 해제
                user.is_locked = False
                user.failed_login_attempts = 0
                user.locked_at = None
                db.commit()
            else:
                return {"error": "account_locked", "message": "계정이 잠겨있습니다. 30분 후 다시 시도해주세요."}

        # 패스워드 검증
        if not verify_password(password, user.password_hash):
            # 로그인 실패 처리
            current_attempts = user.failed_login_attempts or 0
            print(f"🔍 로그인 실패 - 현재 실패 횟수: {current_attempts}")
            user.failed_login_attempts = current_attempts + 1
            user.last_failed_login = datetime.now()
            print(f"🔍 실패 횟수 증가 후: {user.failed_login_attempts}")
            
            # 5회 실패 시 계정 잠금
            if user.failed_login_attempts >= 5:
                user.is_locked = True
                user.locked_at = datetime.now()
                print(f"🔒 계정 잠금 설정 - is_locked: {user.is_locked}, locked_at: {user.locked_at}")
                db.commit()
                print(f"🔍 DB 커밋 완료 - 계정 잠금")
                return {"error": "account_locked", "message": "5회 로그인 실패로 계정이 잠겼습니다. 30분 후 다시 시도해주세요."}
            
            db.commit()
            print(f"🔍 DB 커밋 완료 - 실패 횟수: {user.failed_login_attempts}")
            return {"error": "invalid_credentials", "message": f"메일 또는 비밀번호를 확인해주세요. (남은 시도: {5 - user.failed_login_attempts}회)"}
        
        # 로그인 성공 시 실패 카운터 초기화 (None 처리 포함)
        if user.failed_login_attempts and user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.last_failed_login = None
            db.commit()

        # 사용자 정보 반환
        return {
            "user_id": user.user_id,
            "user_uuid": user.user_uuid,
            "email": user.email,
            "name": user.name,
            "user_type": user.user_type,
            "phone_number": user.phone_number,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
        
    except Exception as e:
        print(f"Authentication error: {e}")
        return None
    finally:
        if close_db:
            db.close()

# JWT 토큰 관련 함수들
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_api_key_dependency(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """API 키 검증 의존성 (데이터베이스 기반)"""
    # Bearer 토큰에서 API 키 추출
    api_key = credentials.credentials
    
    token_info = TokenManager.verify_api_key(api_key, db)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_info["user_uuid"]

def get_token_id_dependency(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """API 키 검증 의존성 (데이터베이스 기반)"""
    # Bearer 토큰에서 API 키 추출
    api_key = credentials.credentials
    
    token_info = TokenManager.verify_api_key(api_key, db)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_info["token_id"]

# 사용자 관리 (데이터베이스 기반)
def create_user(user_id: str, email: str, name: str, user_type: str, password: str, phone_number: Optional[str] = None, db: Session = None) -> Dict:
    """사용자 생성"""
    if db is None:
        db = next(get_db())
    
    # 기존 사용자 확인
    existing_user = db.query(User).filter(User.user_id == user_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # 사용자 타입 검증 및 변환
    valid_user_types = ["개인", "조직", "A01", "A02"]  # A01: 개인, A02: 조직
    if user_type not in valid_user_types:
        raise HTTPException(status_code=400, detail="user_type must be '개인', '조직', 'A01', or 'A02'")
    
    # 한글 타입을 코드로 변환
    if user_type == "개인":
        user_type_code = "A01"
    elif user_type == "조직":
        user_type_code = "A02"
    else:
        user_type_code = user_type  # 이미 A01, A02인 경우
    
    # 패스워드 해시화
    password_hash = hash_password(password)
    
    # 새 사용자 생성
    new_user = User(
        user_id=user_id,
        email=email,
        name=name,
        user_type=user_type_code,
        phone_number=phone_number,
        password_hash=password_hash
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 메모리 기반 저장도 유지 (기존 코드 호환성)
    user_info = {
        "user_id": user_id,
        "user_uuid": new_user.user_uuid,
        "email": email,
        "name": name,
        "user_type": user_type_code,
        "phone_number": phone_number,
        "password_hash": password_hash,
        "created_at": new_user.created_at.isoformat(),
        "is_active": True
    }
    users_db[user_id] = user_info
    
    return user_info

def get_user(user_identifier: str, db: Session = None) -> Optional[Dict]:
    """사용자 정보 조회 (user_id 또는 user_uuid로 검색 가능)"""
    # 먼저 메모리에서 확인 (user_id 기준)
    if user_identifier in users_db:
        return users_db[user_identifier]
    
    # 데이터베이스에서 조회
    if db is None:
        db = next(get_db())
    
    # user_id로 먼저 검색
    user = db.query(User).filter(User.user_id == user_identifier).first()
    
    # user_id로 찾지 못하면 user_uuid로 검색
    if not user:
        user = db.query(User).filter(User.user_uuid == user_identifier).first()
    
    if user:
        user_info = {
            "user_id": user.user_id,
            "user_uuid": user.user_uuid,
            "email": user.email,
            "name": user.name,
            "user_type": user.user_type,
            "phone_number": user.phone_number,
            "created_at": user.created_at.isoformat(),
            "is_active": user.is_active
        }
        # 메모리에도 캐시 (user_id 기준)
        users_db[user.user_id] = user_info
        return user_info
    
    return None