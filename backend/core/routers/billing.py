from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# 절대 경로로 import 수정
from core.database import get_db, User, MonthlyBilling
from core.auth import verify_token
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/billing",
    tags=["billing"],
    responses={404: {"description": "Not found"}},
)

# Pydantic 모델들
class MonthlyBillingResponse(BaseModel):
    """월별 빌링 응답 모델"""
    id: int
    user_uuid: str
    year: int
    month: int
    total_requests: int
    total_duration: float  # 총 처리 시간 (초)
    total_cost: float
    currency: str
    status: str  # "pending", "paid", "overdue"
    created_at: str
    due_date: str
    paid_at: Optional[str]

class BillingHistoryResponse(BaseModel):
    """빌링 이력 응답 모델"""
    id: int
    user_uuid: str
    billing_period: str  # "2024-01"
    amount: float
    currency: str
    payment_method: str
    transaction_id: Optional[str]
    status: str
    created_at: str
    paid_at: Optional[str]
    description: Optional[str]

class UsageSummary(BaseModel):
    """사용량 요약 모델"""
    current_month_requests: int
    current_month_duration: float
    current_month_cost: float
    previous_month_requests: int
    previous_month_duration: float
    previous_month_cost: float
    total_requests: int
    total_duration: float
    total_cost: float
    currency: str

class BillingSettings(BaseModel):
    """빌링 설정 모델"""
    auto_payment: bool
    payment_method_id: Optional[int]
    billing_email: str
    invoice_language: str = "ko"
    currency: str = "KRW"

class InvoiceRequest(BaseModel):
    """인보이스 요청 모델"""
    billing_id: int
    format: str = "pdf"  # "pdf", "html"
    language: str = "ko"

class CostCalculation(BaseModel):
    """비용 계산 모델"""
    base_cost: float
    duration_cost: float
    additional_fees: float
    discount: float
    total_cost: float
    currency: str
    calculation_details: Dict[str, Any]

@router.get("/current", summary="현재 월 빌링 정보")
async def get_current_billing(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> MonthlyBillingResponse:
    """
    현재 월의 빌링 정보를 조회합니다.
    """
    logger.info(f"🔍 현재 월 빌링 정보 조회 - 사용자: {current_user}")
    
    try:
        # 현재 년월 계산
        now = datetime.utcnow()
        current_year = now.year
        current_month = now.month
        
        # 현재 월 빌링 정보 조회
        billing = db.query(MonthlyBilling).filter(
            MonthlyBilling.user_uuid == current_user,
            MonthlyBilling.year == current_year,
            MonthlyBilling.month == current_month
        ).first()
        
        if not billing:
            # 빌링 정보가 없으면 기본값으로 생성
            billing = MonthlyBilling(
                user_uuid=current_user,
                year=current_year,
                month=current_month,
                total_requests=0,
                total_duration=0.0,
                total_cost=0.0,
                currency="KRW",
                status="pending"
            )
        
        return MonthlyBillingResponse(
            id=billing.id if billing.id else 0,
            user_uuid=billing.user_uuid,
            year=billing.year,
            month=billing.month,
            total_requests=billing.total_requests,
            total_duration=billing.total_duration,
            total_cost=billing.total_cost,
            currency=billing.currency,
            status=billing.status,
            created_at=billing.created_at.isoformat() if billing.created_at else datetime.utcnow().isoformat(),
            due_date=(datetime.utcnow() + timedelta(days=30)).isoformat(),
            paid_at=billing.paid_at.isoformat() if billing.paid_at else None
        )
        
    except Exception as e:
        logger.error(f"❌ 현재 월 빌링 정보 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="빌링 정보 조회 중 오류가 발생했습니다."
        )

@router.get("/history", summary="빌링 이력 조회")
async def get_billing_history(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    limit: int = Query(12, description="조회할 개수"),
    offset: int = Query(0, description="건너뛸 개수")
) -> List[MonthlyBillingResponse]:
    """
    사용자의 빌링 이력을 조회합니다.
    
    - **limit**: 조회할 빌링 이력 수 (기본값: 12개월)
    - **offset**: 건너뛸 빌링 이력 수 (기본값: 0)
    """
    logger.info(f"📋 빌링 이력 조회 - 사용자: {current_user}")
    
    try:
        # 빌링 이력 조회 로직 (실제 구현 필요)
        # billing_history = get_user_billing_history(current_user.user_uuid, limit, offset, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 빌링 이력 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="빌링 이력 조회 중 오류가 발생했습니다."
        )

@router.get("/usage-summary", summary="사용량 요약")
async def get_usage_summary(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> UsageSummary:
    """
    사용자의 전체 사용량 요약 정보를 조회합니다.
    """
    logger.info(f"📊 사용량 요약 조회 - 사용자: {current_user}")
    
    try:
        # 사용량 요약 계산 로직 (실제 구현 필요)
        # summary = calculate_usage_summary(current_user.user_uuid, db)
        
        return UsageSummary(
            current_month_requests=0,
            current_month_duration=0.0,
            current_month_cost=0.0,
            previous_month_requests=0,
            previous_month_duration=0.0,
            previous_month_cost=0.0,
            total_requests=0,
            total_duration=0.0,
            total_cost=0.0,
            currency="KRW"
        )
        
    except Exception as e:
        logger.error(f"❌ 사용량 요약 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용량 요약 조회 중 오류가 발생했습니다."
        )

@router.get("/settings", summary="빌링 설정 조회")
async def get_billing_settings(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> BillingSettings:
    """
    사용자의 빌링 설정을 조회합니다.
    """
    logger.info(f"⚙️ 빌링 설정 조회 - 사용자: {current_user}")
    
    try:
        # 빌링 설정 조회 로직 (실제 구현 필요)
        # settings = get_user_billing_settings(current_user.user_uuid, db)
        
        return BillingSettings(
            auto_payment=False,
            payment_method_id=None,
            billing_email="user@example.com",  # current_user는 이제 str이므로 기본값 사용
            invoice_language="ko",
            currency="KRW"
        )
        
    except Exception as e:
        logger.error(f"❌ 빌링 설정 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="빌링 설정 조회 중 오류가 발생했습니다."
        )

@router.put("/settings", summary="빌링 설정 수정")
async def update_billing_settings(
    settings: BillingSettings,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    사용자의 빌링 설정을 수정합니다.
    
    - **auto_payment**: 자동 결제 여부
    - **payment_method_id**: 기본 결제 수단 ID
    - **billing_email**: 빌링 이메일 주소
    - **invoice_language**: 인보이스 언어 (ko, en)
    - **currency**: 통화 (KRW, USD)
    """
    logger.info(f"🔧 빌링 설정 수정 - 사용자: {current_user}")
    
    try:
        # 빌링 설정 수정 로직 (실제 구현 필요)
        # update_user_billing_settings(current_user.user_uuid, settings, db)
        
        logger.info(f"✅ 빌링 설정 수정 완료 - 사용자: {current_user}")
        return {
            "status": "success",
            "message": "빌링 설정이 성공적으로 수정되었습니다."
        }
        
    except Exception as e:
        logger.error(f"❌ 빌링 설정 수정 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="빌링 설정 수정 중 오류가 발생했습니다."
        )

@router.get("/calculate-cost", summary="비용 계산")
async def calculate_cost(
    requests: int = Query(..., description="요청 수"),
    duration: float = Query(..., description="총 처리 시간 (초)"),
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> CostCalculation:
    """
    주어진 사용량에 대한 비용을 계산합니다.
    
    - **requests**: 요청 수
    - **duration**: 총 처리 시간 (초)
    """
    logger.info(f"💰 비용 계산 - 사용자: {current_user}, 요청: {requests}, 시간: {duration}")
    
    try:
        # 비용 계산 로직 (실제 구현 필요)
        # cost_details = calculate_usage_cost(requests, duration, current_user.user_uuid, db)
        
        # 예시 계산
        base_cost = requests * 10  # 요청당 10원
        duration_cost = duration * 5  # 초당 5원
        additional_fees = 0
        discount = 0
        total_cost = base_cost + duration_cost + additional_fees - discount
        
        return CostCalculation(
            base_cost=base_cost,
            duration_cost=duration_cost,
            additional_fees=additional_fees,
            discount=discount,
            total_cost=total_cost,
            currency="KRW",
            calculation_details={
                "request_rate": 10,
                "duration_rate": 5,
                "total_requests": requests,
                "total_duration": duration
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 비용 계산 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비용 계산 중 오류가 발생했습니다."
        )

@router.post("/invoice", summary="인보이스 생성")
async def generate_invoice(
    invoice_request: InvoiceRequest,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    특정 빌링에 대한 인보이스를 생성합니다.
    
    - **billing_id**: 인보이스를 생성할 빌링 ID
    - **format**: 인보이스 형식 (pdf, html)
    - **language**: 인보이스 언어 (ko, en)
    """
    logger.info(f"📄 인보이스 생성 - 빌링 ID: {invoice_request.billing_id}, 사용자: {current_user}")
    
    try:
        # 빌링 정보 조회 및 권한 확인
        billing = db.query(MonthlyBilling).filter(
            MonthlyBilling.id == invoice_request.billing_id,
            MonthlyBilling.user_uuid == current_user
        ).first()
        
        if not billing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="빌링 정보를 찾을 수 없습니다."
            )
        
        # 인보이스 생성 로직 (실제 구현 필요)
        # invoice_url = generate_invoice_file(billing, invoice_request, db)
        
        logger.info(f"✅ 인보이스 생성 완료 - 빌링 ID: {invoice_request.billing_id}")
        return {
            "status": "success",
            "message": "인보이스가 성공적으로 생성되었습니다.",
            "invoice_url": "https://example.com/invoices/generated_invoice.pdf",
            "format": invoice_request.format,
            "language": invoice_request.language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 인보이스 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인보이스 생성 중 오류가 발생했습니다."
        )

@router.post("/pay/{billing_id}", summary="빌링 결제")
async def pay_billing(
    billing_id: int,
    payment_method_id: Optional[int] = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    특정 빌링에 대한 결제를 처리합니다.
    
    - **payment_method_id**: 사용할 결제 수단 ID (선택사항, 기본 결제 수단 사용)
    """
    logger.info(f"💳 빌링 결제 - 빌링 ID: {billing_id}, 사용자: {current_user}")
    
    try:
        # 빌링 정보 조회 및 권한 확인
        billing = db.query(MonthlyBilling).filter(
            MonthlyBilling.id == billing_id,
            MonthlyBilling.user_uuid == current_user
        ).first()
        
        if not billing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="빌링 정보를 찾을 수 없습니다."
            )
        
        if billing.status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 결제된 빌링입니다."
            )
        
        # 결제 처리 로직 (실제 구현 필요)
        # payment_result = process_billing_payment(billing, payment_method_id, db)
        
        logger.info(f"✅ 빌링 결제 완료 - 빌링 ID: {billing_id}")
        return {
            "status": "success",
            "message": "결제가 성공적으로 처리되었습니다.",
            "transaction_id": "generated_transaction_id",
            "amount": billing.total_cost,
            "currency": billing.currency
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 빌링 결제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 처리 중 오류가 발생했습니다."
        )

@router.get("/payment-history", summary="결제 이력 조회")
async def get_payment_history(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    limit: int = Query(20, description="조회할 개수"),
    offset: int = Query(0, description="건너뛸 개수")
) -> List[BillingHistoryResponse]:
    """
    사용자의 결제 이력을 조회합니다.
    
    - **limit**: 조회할 결제 이력 수 (기본값: 20)
    - **offset**: 건너뛸 결제 이력 수 (기본값: 0)
    """
    logger.info(f"📋 결제 이력 조회 - 사용자: {current_user}")
    
    try:
        # 결제 이력 조회 로직 (실제 구현 필요)
        # payment_history = get_user_payment_history(current_user.user_uuid, limit, offset, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 결제 이력 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 이력 조회 중 오류가 발생했습니다."
        )

# 월별 빌링 관련 엔드포인트 (기존 monthly-billing 엔드포인트와 통합)
@router.get("/monthly/{year}/{month}", summary="특정 월 빌링 조회")
async def get_monthly_billing(
    year: int,
    month: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> MonthlyBillingResponse:
    """
    특정 년월의 빌링 정보를 조회합니다.
    
    - **year**: 조회할 년도
    - **month**: 조회할 월
    """
    logger.info(f"🔍 특정 월 빌링 조회 - {year}-{month:02d}, 사용자: {current_user}")
    
    try:
        # 특정 월 빌링 정보 조회
        billing = db.query(MonthlyBilling).filter(
            MonthlyBilling.user_uuid == current_user,
            MonthlyBilling.year == year,
            MonthlyBilling.month == month
        ).first()
        
        if not billing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 월의 빌링 정보를 찾을 수 없습니다."
            )
        
        return MonthlyBillingResponse(
            id=billing.id,
            user_uuid=billing.user_uuid,
            year=billing.year,
            month=billing.month,
            total_requests=billing.total_requests,
            total_duration=billing.total_duration,
            total_cost=billing.total_cost,
            currency=billing.currency,
            status=billing.status,
            created_at=billing.created_at.isoformat(),
            due_date=(billing.created_at + timedelta(days=30)).isoformat(),
            paid_at=billing.paid_at.isoformat() if billing.paid_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 특정 월 빌링 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="빌링 정보 조회 중 오류가 발생했습니다."
        )