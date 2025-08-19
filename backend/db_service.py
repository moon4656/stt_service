from sqlalchemy.orm import Session
from database import TranscriptionRequest, TranscriptionResponse, APIUsageLog
from typing import Optional, Dict, List
import json
import time
import logging
from datetime import datetime, timezone

# Logger 설정
logger = logging.getLogger(__name__)

class TranscriptionService:
    """음성 변환 관련 데이터베이스 서비스"""
    
    def __init__(self, db: Session):
        self.db = db

    def create_request(self, 
                       user_uuid: Optional[str] = None, 
                       filename: str = None, 
                       file_size: int = None,
                       service_name: str = None,
                       model_name: str = None,
                       language: str = None,
                       audio_duration: float = None,
                       stored_file_path: str = None,
                       service_requested: str = None,
                       client_ip: str = None,
                       user_agent: str = None,
                       duration: float = None,
                       fallback_enabled: bool = True,   
                       ) -> TranscriptionRequest:
        """새로운 음성 변환 요청을 생성합니다."""
        file_extension = filename.split('.')[-1] if filename and '.' in filename else ''
        request = TranscriptionRequest(
            user_uuid=user_uuid,  # user_uuid 파라미터 사용
            filename=filename,
            file_size=file_size,
            file_extension=file_extension,
            service_provider=service_requested,
            client_ip=client_ip,
            duration=duration,
            status="processing"
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def create_response(self, request_id: str, transcription_text: str,
                       summary_text: Optional[str] = None,
                       service_used: str = "",
                       processing_time: float = 0.0,
                       duration: float = 0.0,
                       success: bool = True,
                       error_message: Optional[str] = None,
                       service_provider: str = "",
                       audio_duration_minutes: float = 0.0,
                       tokens_used: float = 0.0,
                       response_data: Optional[str] = None,
                       confidence_score: Optional[float] = None,
                       language_detected: Optional[str] = None) -> TranscriptionResponse:
        """음성 변환 응답을 저장합니다 (새로운 컬럼들 포함)."""

        logger.info(f"✅ transcription_text ============================== {transcription_text}")

        word_count = len(transcription_text.split()) if transcription_text else 0
        
        logger.info(f"✅ word_count ============================== {word_count}")
        logger.info(f"✅ audio_duration_minutes ============================== {audio_duration_minutes}")
        
        response = TranscriptionResponse(
            request_id=request_id,
            transcribed_text=transcription_text,
            summary_text=summary_text,
            confidence_score=confidence_score,
            language_detected=language_detected,
            duration=duration,
            word_count=word_count,
            response_data=response_data,
            service_provider=service_provider,
            audio_duration_minutes=audio_duration_minutes,
            tokens_used=tokens_used
        )
        logger.info(f"✅ response Test ============================== 1")
        
        logger.info(f"✅ response ============================== {response}")
        
        try:
            self.db.add(response)
            self.db.commit()
            self.db.refresh(response)
            logger.info(f"✅ Response successfully saved to database")
            return response
        except Exception as e:
            logger.error(f"❌ Error saving response to database: {str(e)}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            self.db.rollback()
            raise e
    
    @staticmethod
    def create_request_static(db: Session, user_uuid: Optional[str], filename: str, 
                      file_size: int, file_extension: str) -> TranscriptionRequest:
        """새로운 음성 변환 요청을 생성합니다 (기존 호환성용)."""
        request = TranscriptionRequest(
            user_uuid=user_uuid,
            filename=filename,
            file_size=file_size,
            file_extension=file_extension,
            status="processing"
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
    
    @staticmethod
    def update_request_with_rid(db: Session, request_id: str, response_rid: str):
        """요청에 STT API Response RID를 업데이트합니다."""
        request = db.query(TranscriptionRequest).filter(TranscriptionRequest.request_id == request_id).first()
        if request:
            request.response_rid = response_rid
            db.commit()

    @staticmethod
    def update_file_path(db: Session, request_id: str, file_path: str) -> bool:
        """요청의 파일 경로를 업데이트합니다."""
        try:
            request = db.query(TranscriptionRequest).filter(TranscriptionRequest.request_id == request_id).first()
            
            if request:
                request.file_path = file_path
                db.commit()
                logger.info(f"✅ 파일 경로 업데이트 완료 - ID: {request_id}, Path: {file_path}")
                return True
            else:
                logger.error(f"❌ 요청을 찾을 수 없음 - ID: {request_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 파일 경로 업데이트 실패: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def complete_request(db: Session, request_id: str, status: str = "completed", 
                        error_message: Optional[str] = None):
        """요청을 완료 상태로 업데이트합니다."""
        request = db.query(TranscriptionRequest).filter(TranscriptionRequest.request_id == request_id).first()
        if request:
            request.status = status
            request.completed_at = datetime.now(timezone.utc)
            if request.created_at:
                request.processing_time = (datetime.now(timezone.utc) - request.created_at).total_seconds()
            if error_message:
                request.error_message = error_message
            db.commit()
    
    @staticmethod
    def create_response_from_daglo(db: Session, request_id: str, daglo_response: Dict, 
                       summary_text: Optional[str] = None) -> TranscriptionResponse:
        """음성 변환 응답을 저장합니다."""
        # Daglo 응답에서 필요한 정보 추출
        transcribed_text = ""
        confidence_score = None
        language_detected = None
        duration = None
        word_count = 0
        
        logger.info(f"✅ daglo_response ============================== {daglo_response}")
        
        # Daglo API 응답 구조에 따라 데이터 추출 (sttResults.transcript 우선)
        if 'sttResults' in daglo_response and daglo_response['sttResults']:
            stt_results = daglo_response['sttResults']
            if isinstance(stt_results, list) and len(stt_results) > 0:
                # sttResults가 리스트인 경우 첫 번째 요소에서 transcript 추출
                transcribed_text = stt_results[0].get('transcript', '') if isinstance(stt_results[0], dict) else ''
            elif isinstance(stt_results, dict):
                # sttResults가 딕셔너리인 경우
                transcribed_text = stt_results.get('transcript', '')
        elif "text" in daglo_response:
            transcribed_text = daglo_response["text"]
        
        logger.info(f"✅ daglo_response transcribed_text ============================== {transcribed_text}")
        
        word_count = len(transcribed_text.split()) if transcribed_text else 0
        
        logger.info(f"✅ daglo_response word_count ============================== {word_count}")
        
        if "confidence" in daglo_response:
            confidence_score = daglo_response["confidence"]
        
        if "language" in daglo_response:
            language_detected = daglo_response["language"]
        
        if "duration" in daglo_response:
            duration = daglo_response["duration"]
        
        logger.info(f"✅ daglo_response test ============================== 001")
        
        # response_data 크기 제한 (최대 50KB)
        response_data_str = json.dumps(daglo_response, ensure_ascii=False)
        if len(response_data_str) > 50000:  # 50KB 제한
            # 큰 데이터는 요약된 버전만 저장
            simplified_response = {
                "text": daglo_response.get("text", "")[:1000] + "...(truncated)" if len(daglo_response.get("text", "")) > 1000 else daglo_response.get("text", ""),
                "confidence": daglo_response.get("confidence"),
                "language": daglo_response.get("language"),
                "duration": daglo_response.get("duration"),
                "processing_time": daglo_response.get("processing_time"),
                "error": daglo_response.get("error"),
                "note": "Original response was truncated due to size limit"
            }
            response_data_str = json.dumps(simplified_response, ensure_ascii=False)
            logger.warning(f"⚠️ Response data truncated due to size limit. Original size: {len(json.dumps(daglo_response, ensure_ascii=False))} bytes")
        
        response = TranscriptionResponse(
            request_id=request_id,
            transcribed_text=transcribed_text,
            summary_text=summary_text,
            confidence_score=confidence_score,
            language_detected=language_detected,
            duration=duration,
            word_count=word_count,
            response_data=response_data_str
        )
        
        logger.info(f"✅ daglo_response test ============================== 002")
        logger.info(f"✅ daglo_response response ============================== {response}")
        
        try:
            db.add(response)
            db.commit()
            db.refresh(response)
            logger.info(f"✅ Response successfully saved to database")
            return response
        except Exception as e:
            logger.error(f"❌ Error saving response to database: {str(e)}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            db.rollback()
            raise e
    
    @staticmethod
    def get_request_by_id(db: Session, request_id: str) -> Optional[TranscriptionRequest]:
        """ID로 요청을 조회합니다."""
        return db.query(TranscriptionRequest).filter(TranscriptionRequest.request_id == request_id).first()
    
    @staticmethod
    def get_user_requests(db: Session, user_uuid: str, limit: int = 50) -> List[TranscriptionRequest]:
        """사용자의 요청 목록을 조회합니다."""
        return db.query(TranscriptionRequest).filter(
            TranscriptionRequest.user_uuid == user_uuid
        ).order_by(TranscriptionRequest.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_request_with_response(db: Session, request_id: str) -> Optional[Dict]:
        """요청과 응답을 함께 조회합니다."""
        request = db.query(TranscriptionRequest).filter(TranscriptionRequest.request_id == request_id).first()
        if not request:
            return None
        
        response = db.query(TranscriptionResponse).filter(
            TranscriptionResponse.request_id == request_id
        ).first()
        
        return {
            "request": request,
            "response": response
        }

class APIUsageService:
    """API 사용 로그 관련 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_usage(self, user_uuid: Optional[str], endpoint: str, method: str, 
                  status_code: int, processing_time: Optional[float] = None,
                  client_ip: Optional[str] = None, user_agent: Optional[str] = None,
                  api_key_hash: Optional[str] = None,
                  request_size: Optional[int] = None, response_size: Optional[int] = None):
        """API 사용 로그를 기록합니다."""
        log = APIUsageLog(
            user_uuid=user_uuid,
            api_key_hash=api_key_hash,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            request_size=request_size,
            response_size=response_size,
            processing_time=processing_time,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        self.db.add(log)
        self.db.commit()
    
    @staticmethod
    def log_api_usage(db: Session, user_uuid: Optional[str], api_key_hash: Optional[str],
                     endpoint: str, method: str, status_code: int,
                     request_size: Optional[int] = None, response_size: Optional[int] = None,
                     processing_time: Optional[float] = None, ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None,
                     success: bool = True):
        """API 사용 로그를 기록합니다 (기존 호환성용)."""
        log = APIUsageLog(
            user_uuid=user_uuid,
            api_key_hash=api_key_hash,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            request_size=request_size,
            response_size=response_size,
            processing_time=processing_time,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(log)
        db.commit()
    
    @staticmethod
    def get_user_usage_stats(db: Session, user_uuid: str, days: int = 30) -> Dict:
        """사용자의 API 사용 통계를 조회합니다."""
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 총 요청 수
        total_requests = db.query(func.count(APIUsageLog.id)).filter(
            APIUsageLog.user_uuid == user_uuid,
            APIUsageLog.created_at >= start_date
        ).scalar()
        
        # 성공 요청 수 (2xx 상태 코드)
        successful_requests = db.query(func.count(APIUsageLog.id)).filter(
            APIUsageLog.user_uuid == user_uuid,
            APIUsageLog.created_at >= start_date,
            APIUsageLog.status_code >= 200,
            APIUsageLog.status_code < 300
        ).scalar()
        
        # 평균 처리 시간
        avg_processing_time = db.query(func.avg(APIUsageLog.processing_time)).filter(
            APIUsageLog.user_uuid == user_uuid,
            APIUsageLog.created_at >= start_date,
            APIUsageLog.processing_time.isnot(None)
        ).scalar()
        
        # 총 데이터 사용량
        total_request_size = db.query(func.sum(APIUsageLog.request_size)).filter(
            APIUsageLog.user_uuid == user_uuid,
            APIUsageLog.created_at >= start_date,
            APIUsageLog.request_size.isnot(None)
        ).scalar() or 0
        
        total_response_size = db.query(func.sum(APIUsageLog.response_size)).filter(
            APIUsageLog.user_uuid == user_uuid,
            APIUsageLog.created_at >= start_date,
            APIUsageLog.response_size.isnot(None)
        ).scalar() or 0
        
        return {
            "period_days": days,
            "total_requests": total_requests or 0,
            "successful_requests": successful_requests or 0,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "avg_processing_time": float(avg_processing_time) if avg_processing_time else 0,
            "total_data_usage": {
                "request_bytes": total_request_size,
                "response_bytes": total_response_size,
                "total_bytes": total_request_size + total_response_size
            }
        }
    
    @staticmethod
    def get_recent_logs(db: Session, user_uuid: str, limit: int = 50) -> List[APIUsageLog]:
        """사용자의 최근 API 사용 로그를 조회합니다."""
        return db.query(APIUsageLog).filter(
            APIUsageLog.user_uuid == user_uuid
        ).order_by(APIUsageLog.created_at.desc()).limit(limit).all()
