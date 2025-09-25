from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

# 절대 경로로 import 수정
from core.database import get_db, APIUsageLog, TranscriptionRequest
from core.auth import verify_token
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
    responses={404: {"description": "Not found"}},
)

# Pydantic 모델들
class SystemStats(BaseModel):
    """시스템 통계 모델"""
    total_users: int
    active_users_today: int
    total_requests_today: int
    total_requests_this_month: int
    average_response_time: float
    success_rate: float
    system_uptime: str
    last_updated: str

class UserStats(BaseModel):
    """사용자 통계 모델"""
    user_uuid: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float
    average_duration: float
    last_request_at: Optional[str]
    most_used_service: str
    request_trend: List[Dict[str, Any]]

class APIUsageStats(BaseModel):
    """API 사용 통계 모델"""
    endpoint: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    average_response_time: float
    last_called_at: str
    usage_trend: List[Dict[str, Any]]

class ServicePerformance(BaseModel):
    """서비스 성능 모델"""
    service_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_processing_time: float
    success_rate: float
    last_request_at: Optional[str]
    performance_trend: List[Dict[str, Any]]

class ErrorLog(BaseModel):
    """에러 로그 모델"""
    id: int
    timestamp: str
    level: str
    message: str
    endpoint: Optional[str]
    user_uuid: Optional[str]
    error_type: str
    stack_trace: Optional[str]

class HealthCheck(BaseModel):
    """헬스 체크 모델"""
    status: str
    timestamp: str
    database_status: str
    stt_services_status: Dict[str, str]
    memory_usage: float
    cpu_usage: float
    disk_usage: float
    uptime: str

@router.get("/health", summary="시스템 헬스 체크")
async def health_check(
    db: Session = Depends(get_db)
) -> HealthCheck:
    """
    시스템의 전반적인 상태를 확인합니다.
    """
    logger.info("🏥 시스템 헬스 체크 수행")
    
    try:
        # 데이터베이스 상태 확인
        try:
            db.execute("SELECT 1")
            db_status = "healthy"
        except Exception:
            db_status = "unhealthy"
        
        # STT 서비스 상태 확인 (실제 구현 필요)
        stt_services = {
            "assemblyai": "healthy",
            "daglo": "healthy"
        }
        
        # 시스템 리소스 사용량 확인 (실제 구현 필요)
        # resource_usage = get_system_resource_usage()
        
        return HealthCheck(
            status="healthy" if db_status == "healthy" else "unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            database_status=db_status,
            stt_services_status=stt_services,
            memory_usage=65.5,  # 예시 값
            cpu_usage=23.2,     # 예시 값
            disk_usage=45.8,    # 예시 값
            uptime="5 days, 12:34:56"
        )
        
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {str(e)}")
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            database_status="unknown",
            stt_services_status={},
            memory_usage=0.0,
            cpu_usage=0.0,
            disk_usage=0.0,
            uptime="unknown"
        )

@router.get("/stats/system", summary="시스템 통계")
async def get_system_stats(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> SystemStats:
    """
    시스템 전체 통계를 조회합니다.
    
    관리자 권한이 필요합니다.
    """
    logger.info(f"📊 시스템 통계 조회 - 사용자: {current_user}")
    
    try:
        # 관리자 권한 확인 (실제 구현 필요)
        # if not is_admin(current_user):
        #     raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        
        # 시스템 통계 계산 (실제 구현 필요)
        # stats = calculate_system_statistics(db)
        
        return SystemStats(
            total_users=0,
            active_users_today=0,
            total_requests_today=0,
            total_requests_this_month=0,
            average_response_time=0.0,
            success_rate=0.0,
            system_uptime="5 days, 12:34:56",
            last_updated=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 시스템 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시스템 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/stats/user", summary="사용자 통계")
async def get_user_stats(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    days: int = Query(30, description="조회할 일수")
) -> UserStats:
    """
    현재 사용자의 사용 통계를 조회합니다.
    
    - **days**: 조회할 일수 (기본값: 30일)
    """
    logger.info(f"📊 사용자 통계 조회 - 사용자: {current_user}, 기간: {days}일")
    
    try:
        # 사용자 통계 계산 (실제 구현 필요)
        # stats = calculate_user_statistics(current_user.user_uuid, days, db)
        
        return UserStats(
            user_uuid=current_user,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            total_duration=0.0,
            average_duration=0.0,
            last_request_at=None,
            most_used_service="assemblyai",
            request_trend=[]
        )
        
    except Exception as e:
        logger.error(f"❌ 사용자 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/stats/api", summary="API 사용 통계")
async def get_api_usage_stats(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    days: int = Query(7, description="조회할 일수")
) -> List[APIUsageStats]:
    """
    API 엔드포인트별 사용 통계를 조회합니다.
    
    - **days**: 조회할 일수 (기본값: 7일)
    
    관리자 권한이 필요합니다.
    """
    logger.info(f"📊 API 사용 통계 조회 - 사용자: {current_user}, 기간: {days}일")
    
    try:
        # 관리자 권한 확인 (실제 구현 필요)
        # if not is_admin(current_user):
        #     raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        
        # API 사용 통계 계산 (실제 구현 필요)
        # api_stats = calculate_api_usage_statistics(days, db)
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API 사용 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 사용 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/stats/services", summary="STT 서비스 성능 통계")
async def get_service_performance(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    days: int = Query(7, description="조회할 일수")
) -> List[ServicePerformance]:
    """
    STT 서비스별 성능 통계를 조회합니다.
    
    - **days**: 조회할 일수 (기본값: 7일)
    """
    logger.info(f"📊 STT 서비스 성능 통계 조회 - 사용자: {current_user}, 기간: {days}일")
    
    try:
        # STT 서비스 성능 통계 계산 (실제 구현 필요)
        # service_stats = calculate_service_performance_statistics(days, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ STT 서비스 성능 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STT 서비스 성능 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/logs/errors", summary="에러 로그 조회")
async def get_error_logs(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    level: Optional[str] = Query(None, description="로그 레벨 필터"),
    limit: int = Query(100, description="조회할 로그 수"),
    offset: int = Query(0, description="건너뛸 로그 수")
) -> List[ErrorLog]:
    """
    시스템 에러 로그를 조회합니다.
    
    - **level**: 로그 레벨 필터 (ERROR, WARNING, INFO)
    - **limit**: 조회할 로그 수 (기본값: 100)
    - **offset**: 건너뛸 로그 수 (기본값: 0)
    
    관리자 권한이 필요합니다.
    """
    logger.info(f"📋 에러 로그 조회 - 사용자: {current_user}, 레벨: {level}")
    
    try:
        # 관리자 권한 확인 (실제 구현 필요)
        # if not is_admin(current_user):
        #     raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        
        # 에러 로그 조회 (실제 구현 필요)
        # error_logs = get_system_error_logs(level, limit, offset, db)
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 에러 로그 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="에러 로그 조회 중 오류가 발생했습니다."
        )

@router.get("/usage/daily", summary="일별 사용량 통계")
async def get_daily_usage(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    days: int = Query(30, description="조회할 일수")
) -> List[Dict[str, Any]]:
    """
    일별 사용량 통계를 조회합니다.
    
    - **days**: 조회할 일수 (기본값: 30일)
    """
    logger.info(f"📊 일별 사용량 통계 조회 - 사용자: {current_user}, 기간: {days}일")
    
    try:
        # 일별 사용량 통계 계산 (실제 구현 필요)
        # daily_usage = calculate_daily_usage_statistics(current_user.user_uuid, days, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 일별 사용량 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="일별 사용량 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/usage/hourly", summary="시간별 사용량 통계")
async def get_hourly_usage(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    hours: int = Query(24, description="조회할 시간")
) -> List[Dict[str, Any]]:
    """
    시간별 사용량 통계를 조회합니다.
    
    - **hours**: 조회할 시간 (기본값: 24시간)
    """
    logger.info(f"📊 시간별 사용량 통계 조회 - 사용자: {current_user}, 기간: {hours}시간")
    
    try:
        # 시간별 사용량 통계 계산 (실제 구현 필요)
        # hourly_usage = calculate_hourly_usage_statistics(current_user.user_uuid, hours, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 시간별 사용량 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시간별 사용량 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/alerts", summary="시스템 알림 조회")
async def get_system_alerts(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    severity: Optional[str] = Query(None, description="알림 심각도 필터")
) -> List[Dict[str, Any]]:
    """
    시스템 알림을 조회합니다.
    
    - **severity**: 알림 심각도 필터 (critical, warning, info)
    
    관리자 권한이 필요합니다.
    """
    logger.info(f"🚨 시스템 알림 조회 - 사용자: {current_user}, 심각도: {severity}")
    
    try:
        # 관리자 권한 확인 (실제 구현 필요)
        # if not is_admin(current_user):
        #     raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
        
        # 시스템 알림 조회 (실제 구현 필요)
        # alerts = get_system_alerts_from_db(severity, db)
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 시스템 알림 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시스템 알림 조회 중 오류가 발생했습니다."
        )

@router.get("/performance/response-times", summary="응답 시간 통계")
async def get_response_time_stats(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    endpoint: Optional[str] = Query(None, description="특정 엔드포인트 필터"),
    hours: int = Query(24, description="조회할 시간")
) -> Dict[str, Any]:
    """
    API 응답 시간 통계를 조회합니다.
    
    - **endpoint**: 특정 엔드포인트 필터
    - **hours**: 조회할 시간 (기본값: 24시간)
    """
    logger.info(f"⏱️ 응답 시간 통계 조회 - 사용자: {current_user.user_uuid}, 엔드포인트: {endpoint}")
    
    try:
        # 응답 시간 통계 계산 (실제 구현 필요)
        # response_time_stats = calculate_response_time_statistics(endpoint, hours, db)
        
        return {
            "average_response_time": 0.0,
            "min_response_time": 0.0,
            "max_response_time": 0.0,
            "p95_response_time": 0.0,
            "p99_response_time": 0.0,
            "total_requests": 0,
            "time_series": []
        }
        
    except Exception as e:
        logger.error(f"❌ 응답 시간 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="응답 시간 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/dashboard", summary="모니터링 대시보드 데이터")
async def get_dashboard_data(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    모니터링 대시보드에 필요한 모든 데이터를 한 번에 조회합니다.
    """
    logger.info(f"📊 대시보드 데이터 조회 - 사용자: {current_user}")
    
    try:
        # 대시보드 데이터 수집 (실제 구현 필요)
        # dashboard_data = collect_dashboard_data(current_user.user_uuid, db)
        
        return {
            "user_stats": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_duration": 0.0
            },
            "recent_activity": [],
            "service_status": {
                "assemblyai": "healthy",
                "daglo": "healthy"
            },
            "usage_trend": [],
            "cost_summary": {
                "current_month": 0.0,
                "previous_month": 0.0,
                "currency": "KRW"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 대시보드 데이터 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대시보드 데이터 조회 중 오류가 발생했습니다."
        )