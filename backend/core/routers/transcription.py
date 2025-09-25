from fastapi import APIRouter, UploadFile, File, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from core.auth import verify_service_token, get_token_id_from_token

router = APIRouter(
    prefix="/transcribe",
    tags=["음성변환"]
)

@router.post("/", summary="음성 파일을 텍스트로 변환")
async def transcribe_audio(
    request: Request, 
    file: UploadFile = File(...), 
    service: Optional[str] = None,
    fallback: bool = True,
    summarization: bool = False,
    db: Session = Depends(get_db)
):
    # 기존 transcribe_audio 로직 이동
    pass

@router.post("/protected", summary="API 키 인증 음성 변환")
async def transcribe_audio_protected(
    request: Request,
    file: UploadFile = File(...), 
    service: Optional[str] = None,
    fallback: bool = True,
    summarization: bool = False,
    current_user: str = Depends(verify_service_token),
    token_id: str = Depends(get_token_id_from_token),
    db: Session = Depends(get_db)
):
    # 기존 transcribe_audio_protected 로직 이동
    pass

@router.get("/history", summary="음성 변환 요청 내역 조회")
def get_transcription_history(limit: int = 50, db: Session = Depends(get_db)):
    # 기존 get_transcription_history 로직 이동
    pass

@router.get("/{request_id}", summary="특정 음성 변환 요청 상세 조회")
def get_transcription_detail(request_id: str, db: Session = Depends(get_db)):
    # 기존 get_transcription_detail 로직 이동
    pass