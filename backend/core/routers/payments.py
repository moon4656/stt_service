from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# 절대 경로로 import 수정
from core.database import get_db, User, Payment
from core.auth import verify_token
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    responses={404: {"description": "Not found"}},
)

# Pydantic 모델들
class PaymentCreate(BaseModel):
    """결제 생성 요청 모델"""
    amount: float
    currency: str = "KRW"
    payment_method_id: int
    description: Optional[str] = None

class PaymentResponse(BaseModel):
    """결제 응답 모델"""
    id: int
    user_uuid: str
    amount: float
    currency: str
    status: str
    payment_method: str
    transaction_id: Optional[str]
    created_at: str
    description: Optional[str]

class PaymentMethodCreate(BaseModel):
    """결제 수단 등록 요청 모델"""
    type: str  # "card", "bank_transfer", "paypal"
    card_number: Optional[str] = None
    card_holder_name: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None
    is_default: bool = False

class PaymentMethodResponse(BaseModel):
    """결제 수단 응답 모델"""
    id: int
    type: str
    masked_info: str  # 마스킹된 카드번호 또는 계좌번호
    is_default: bool
    is_active: bool
    created_at: str

class RefundRequest(BaseModel):
    """환불 요청 모델"""
    reason: str
    amount: Optional[float] = None  # 부분 환불 시 금액

@router.post("/", summary="결제 생성")
async def create_payment(
    payment_data: PaymentCreate,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    새로운 결제를 생성합니다.
    
    - **amount**: 결제 금액
    - **currency**: 통화 (기본값: KRW)
    - **payment_method_id**: 사용할 결제 수단 ID
    - **description**: 결제 설명 (선택사항)
    """
    logger.info(f"🚀 결제 생성 요청 - 사용자: {current_user}, 금액: {payment_data.amount}")
    
    try:
        # 결제 수단 확인
        # PaymentMethod 모델이 없으므로 임시로 주석 처리
        # payment_method = db.query(PaymentMethod).filter(
        #     PaymentMethod.id == payment_data.payment_method_id,
        #     PaymentMethod.user_uuid == current_user,
        #     PaymentMethod.is_active == True
        # ).first()
        payment_method = None  # 임시 처리
        
        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="결제 수단을 찾을 수 없습니다."
            )
        
        # 결제 처리 로직 (실제 구현 필요)
        # payment_result = process_payment(payment_data, payment_method, current_user)
        
        logger.info(f"🚀 결제 생성 완료 - 사용자: {current_user}")
        return {
            "status": "success",
            "message": "결제가 성공적으로 처리되었습니다.",
            "payment_id": "generated_payment_id",
            "transaction_id": "generated_transaction_id"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결제 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 처리 중 오류가 발생했습니다."
        )

@router.get("/", summary="결제 내역 조회")
async def get_payments(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="결제 상태 필터"),
    limit: int = Query(20, description="조회할 결제 수"),
    offset: int = Query(0, description="건너뛸 결제 수")
) -> List[PaymentResponse]:
    """
    현재 사용자의 결제 내역을 조회합니다.
    
    - **status_filter**: 결제 상태로 필터링 (pending, completed, failed, refunded)
    - **limit**: 조회할 결제 수 (기본값: 20)
    - **offset**: 건너뛸 결제 수 (기본값: 0)
    """
    logger.info(f"🔍 결제 내역 조회 - 사용자: {current_user}")
    
    try:
        # 결제 내역 조회 로직 (실제 구현 필요)
        # payments = get_user_payments(current_user.user_uuid, status_filter, limit, offset, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 결제 내역 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 내역 조회 중 오류가 발생했습니다."
        )

@router.get("/{payment_id}", summary="결제 상세 조회")
async def get_payment(
    payment_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    특정 결제의 상세 정보를 조회합니다.
    """
    logger.info(f"🔍 결제 상세 조회 - ID: {payment_id}, 사용자: {current_user}")
    
    try:
        # 결제 조회 및 권한 확인
        payment = db.query(Payment).filter(
            Payment.payment_id == payment_id,
            Payment.user_uuid == current_user
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="결제를 찾을 수 없습니다."
            )
        
        # 결제 상세 정보 반환 (실제 구현 필요)
        return PaymentResponse(
            id=payment.id,
            user_uuid=payment.user_uuid,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            payment_method="Card",
            transaction_id=payment.transaction_id,
            created_at=payment.created_at.isoformat(),
            description=payment.description
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결제 상세 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 조회 중 오류가 발생했습니다."
        )

@router.post("/{payment_id}/refund", summary="결제 환불")
async def refund_payment(
    payment_id: int,
    refund_data: RefundRequest,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    결제를 환불 처리합니다.
    
    - **reason**: 환불 사유
    - **amount**: 환불 금액 (부분 환불 시, 전액 환불이면 생략)
    """
    logger.info(f"💰 결제 환불 요청 - ID: {payment_id}, 사용자: {current_user.user_uuid}")
    
    try:
        # 결제 조회 및 권한 확인
        payment = db.query(Payment).filter(
            Payment.id == payment_id,
            Payment.user_uuid == current_user.user_uuid
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="결제를 찾을 수 없습니다."
            )
        
        if payment.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="완료된 결제만 환불할 수 있습니다."
            )
        
        # 환불 처리 로직 (실제 구현 필요)
        # refund_result = process_refund(payment, refund_data)
        
        logger.info(f"✅ 결제 환불 완료 - ID: {payment_id}")
        return {
            "status": "success",
            "message": "환불이 성공적으로 처리되었습니다.",
            "refund_id": "generated_refund_id"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결제 환불 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="환불 처리 중 오류가 발생했습니다."
        )

# 결제 수단 관리 엔드포인트
@router.post("/methods", summary="결제 수단 등록")
async def create_payment_method(
    method_data: PaymentMethodCreate,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    새로운 결제 수단을 등록합니다.
    
    - **type**: 결제 수단 유형 (card, bank_transfer, paypal)
    - **card_number**: 카드 번호 (카드 결제 시)
    - **card_holder_name**: 카드 소유자명 (카드 결제 시)
    - **expiry_month**: 만료 월 (카드 결제 시)
    - **expiry_year**: 만료 년 (카드 결제 시)
    - **bank_account**: 계좌 번호 (계좌 이체 시)
    - **bank_name**: 은행명 (계좌 이체 시)
    - **is_default**: 기본 결제 수단 여부
    """
    logger.info(f"🚀 결제 수단 등록 - 사용자: {current_user}, 유형: {method_data.type}")
    
    try:
        # 결제 수단 등록 로직 (실제 구현 필요)
        # new_method = create_new_payment_method(method_data, current_user, db)
        
        logger.info(f"✅ 결제 수단 등록 완료 - 사용자: {current_user}")
        return {
            "status": "success",
            "message": "결제 수단이 성공적으로 등록되었습니다.",
            "method_id": "generated_method_id"
        }
        
    except Exception as e:
        logger.error(f"❌ 결제 수단 등록 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 수단 등록 중 오류가 발생했습니다."
        )

@router.get("/methods", summary="결제 수단 목록")
async def get_payment_methods(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> List[PaymentMethodResponse]:
    """
    현재 사용자의 등록된 결제 수단 목록을 조회합니다.
    """
    logger.info(f"🔍 결제 수단 목록 조회 - 사용자: {current_user}")
    
    try:
        # 결제 수단 목록 조회 로직 (실제 구현 필요)
        # methods = get_user_payment_methods(current_user.user_uuid, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 결제 수단 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 수단 목록 조회 중 오류가 발생했습니다."
        )

@router.put("/methods/{method_id}", summary="결제 수단 수정")
async def update_payment_method(
    method_id: int,
    is_default: bool,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    결제 수단 설정을 수정합니다.
    
    - **is_default**: 기본 결제 수단 여부
    """
    logger.info(f"🔧 결제 수단 수정 - ID: {method_id}, 사용자: {current_user}")
    
    try:
        # PaymentMethod 모델이 없으므로 임시로 주석 처리
        # method = db.query(PaymentMethod).filter(
        #     PaymentMethod.id == method_id,
        #     PaymentMethod.user_uuid == current_user
        # ).first()
        method = None  # 임시 처리
        
        if not method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="결제 수단을 찾을 수 없습니다."
            )
        
        # 결제 수단 수정 로직 (실제 구현 필요)
        # update_payment_method_settings(method, is_default, db)
        
        logger.info(f"✅ 결제 수단 수정 완료 - ID: {method_id}")
        return {
            "status": "success",
            "message": "결제 수단이 성공적으로 수정되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결제 수단 수정 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 수단 수정 중 오류가 발생했습니다."
        )

@router.delete("/methods/{method_id}", summary="결제 수단 삭제")
async def delete_payment_method(
    method_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    결제 수단을 삭제합니다.
    """
    logger.info(f"🗑️ 결제 수단 삭제 - ID: {method_id}, 사용자: {current_user}")
    
    try:
        # PaymentMethod 모델이 없으므로 임시로 주석 처리
        # method = db.query(PaymentMethod).filter(
        #     PaymentMethod.id == method_id,
        #     PaymentMethod.user_uuid == current_user
        # ).first()
        method = None  # 임시 처리
        
        if not method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="결제 수단을 찾을 수 없습니다."
            )
        
        # 결제 수단 삭제 로직 (실제 구현 필요)
        # delete_payment_method_from_db(method, db)
        
        logger.info(f"✅ 결제 수단 삭제 완료 - ID: {method_id}")
        return {
            "status": "success",
            "message": "결제 수단이 성공적으로 삭제되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결제 수단 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결제 수단 삭제 중 오류가 발생했습니다."
        )