import jwt
import datetime
import secrets
import hashlib
from typing import Optional, Dict, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import os
from sqlalchemy.orm import Session
from database import User, get_db
import bcrypt

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
    def generate_api_key(user_id: str, token_id: str, description: str = "") -> Dict:
        """사용자별 API 키 생성"""
        # 동일한 token_id가 이미 존재하는지 확인
        for existing_token in tokens_db.values():
            if existing_token.get("token_id") == token_id and existing_token["user_id"] == user_id:
                raise ValueError(f"Token ID '{token_id}' already exists for this user")
        
        # API 키 생성 (32바이트 랜덤 문자열)
        api_key = secrets.token_urlsafe(32)
        
        # API 키 해시 (저장용)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 토큰 정보
        token_info = {
            "api_key_hash": api_key_hash,
            "token_id": token_id,
            "user_id": user_id,
            "description": description,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "is_active": True,
            "usage_count": 0,
            "last_used": None
        }
        
        # 토큰 저장
        tokens_db[api_key_hash] = token_info
        
        # 히스토리 저장
        token_history_db.append({
            "action": "created",
            "api_key_hash": api_key_hash,
            "token_id": token_id,
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "description": description
        })
        
        return {
            "api_key": api_key,
            "api_key_hash": api_key_hash,
            "token_id": token_id,
            "user_id": user_id,
            "description": description,
            "created_at": token_info["created_at"],
            "is_active": True
        }
    
    @staticmethod
    def verify_api_key(api_key: str) -> Optional[Dict]:
        """API 키 검증"""
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        token_info = tokens_db.get(api_key_hash)
        if not token_info or not token_info["is_active"]:
            return None

def authenticate_user(user_id: str, password: str, db: Session = None) -> Optional[Dict]:
    """사용자 인증 (패스워드 검증)"""
    if db is None:
        db = next(get_db())
    
    try:
        # 데이터베이스에서 사용자 조회
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            return None
        
        # 패스워드 검증
        if not verify_password(password, user.password_hash):
            return None
        
        # 사용자 정보 반환
        return {
            "user_id": user.user_id,
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
        db.close()
    
    @staticmethod
    def revoke_api_key(api_key_hash: str, user_id: str) -> bool:
        """API 키 비활성화"""
        token_info = tokens_db.get(api_key_hash)
        if not token_info or token_info["user_id"] != user_id:
            return False
        
        token_info["is_active"] = False
        token_info["revoked_at"] = datetime.datetime.utcnow().isoformat()
        
        # 히스토리 저장
        token_history_db.append({
            "action": "revoked",
            "api_key_hash": api_key_hash,
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        
        return True
    
    @staticmethod
    def get_user_tokens(user_id: str) -> List[Dict]:
        """사용자의 모든 토큰 조회"""
        user_tokens = []
        for api_key_hash, token_info in tokens_db.items():
            if token_info["user_id"] == user_id:
                # 민감한 정보 제외하고 반환
                safe_token_info = {
                    "api_key_hash": api_key_hash,
                    "token_id": token_info.get("token_id"),
                    "description": token_info["description"],
                    "created_at": token_info["created_at"],
                    "is_active": token_info["is_active"],
                    "usage_count": token_info["usage_count"],
                    "last_used": token_info.get("last_used")
                }
                if "revoked_at" in token_info:
                    safe_token_info["revoked_at"] = token_info["revoked_at"]
                user_tokens.append(safe_token_info)
        
        return user_tokens
    
    @staticmethod
    def get_token_history(user_id: str, limit: int = 50) -> List[Dict]:
        """사용자의 토큰 사용 내역 조회"""
        user_history = [
            history for history in token_history_db 
            if history["user_id"] == user_id
        ]
        
        # 최신 순으로 정렬
        user_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return user_history[:limit]

# JWT 토큰 관련 함수들
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
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

def verify_api_key_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """API 키 검증 의존성"""
    # Bearer 토큰에서 API 키 추출
    api_key = credentials.credentials
    
    token_info = TokenManager.verify_api_key(api_key)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_info["user_id"]

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

def get_user(user_id: str, db: Session = None) -> Optional[Dict]:
    """사용자 정보 조회"""
    # 먼저 메모리에서 확인
    if user_id in users_db:
        return users_db[user_id]
    
    # 데이터베이스에서 조회
    if db is None:
        db = next(get_db())
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user_info = {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "user_type": user.user_type,
            "phone_number": user.phone_number,
            "created_at": user.created_at.isoformat(),
            "is_active": user.is_active
        }
        # 메모리에도 캐시
        users_db[user_id] = user_info
        return user_info
    
    return None