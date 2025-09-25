from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# 절대 경로로 import 수정
from core.database import get_db, User, SubscriptionMaster, SubscriptionPlan
from core.auth import verify_token
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
    responses={404: {"description": "Not found"}},
)

# Pydantic 모델들
class SubscriptionCreate(BaseModel):
    """구독 생성 요청 모델"""
    plan_id: int
    payment_method: str = "card"

class SubscriptionResponse(BaseModel):
    """구독 응답 모델"""
    id: int
    user_uuid: str
    plan_id: int
    plan_name: str
    status: str
    start_date: str
    end_date: str
    auto_renewal: bool

class SubscriptionPlanResponse(BaseModel):
    """구독 요금제 응답 모델"""
    id: int
    name: str
    description: str
    price: float
    currency: str
    duration_months: int
    features: List[str]
    is_active: bool

class SubscriptionChange(BaseModel):
    """구독 변경 요청 모델"""
    new_plan_id: int
    change_type: str  # "upgrade", "downgrade", "change"
    effective_date: Optional[str] = None

@router.post("/", summary="구독 생성")
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    새로운 구독을 생성합니다.
    
    - **plan_id**: 구독할 요금제 ID
    - **payment_method**: 결제 방법 (card, bank_transfer)
    """
    logger.info(f"🚀 구독 생성 요청 - 사용자: {current_user.user_uuid}, 요금제: {subscription_data.plan_id}")
    
    try:
        # 기존 활성 구독 확인
        existing_subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.user_uuid == current_user,
             SubscriptionMaster.subscription_status == "active"
        ).first()
        
        if existing_subscription:
            logger.warning(f"⚠️ 이미 활성 구독 존재 - 사용자: {current_user.user_uuid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 활성화된 구독이 있습니다."
            )
        
        # 요금제 존재 확인
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == subscription_data.plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="요금제를 찾을 수 없습니다."
            )
        
        # 구독 생성 로직 (실제 구현 필요)
        # new_subscription = create_new_subscription(current_user, subscription_data, db)
        
        logger.info(f"✅ 구독 생성 완료 - 사용자: {current_user.user_uuid}")
        return {
            "status": "success",
            "message": "구독이 성공적으로 생성되었습니다.",
            "subscription_id": "generated_id"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="구독 생성 중 오류가 발생했습니다."
        )

@router.get("/", summary="구독 목록 조회")
async def get_subscriptions(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="구독 상태 필터")
) -> List[SubscriptionResponse]:
    """
    현재 사용자의 구독 목록을 조회합니다.
    
    - **status_filter**: 구독 상태로 필터링 (active, inactive, expired)
    """
    logger.info(f"🔍 구독 목록 조회 - 사용자: {current_user.user_uuid}")
    
    try:
        # 구독 목록 조회 로직 (실제 구현 필요)
        # subscriptions = get_user_subscriptions(current_user.user_uuid, status_filter, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 구독 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="구독 목록 조회 중 오류가 발생했습니다."
        )

@router.get("/{subscription_id}", summary="구독 상세 조회")
async def get_subscription(
    subscription_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> SubscriptionResponse:
    """
    특정 구독의 상세 정보를 조회합니다.
    """
    logger.info(f"🔍 구독 상세 조회 - ID: {subscription_id}, 사용자: {current_user.user_uuid}")
    
    try:
        # 구독 조회 및 권한 확인
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.id == subscription_id,
             SubscriptionMaster.user_uuid == current_user
        ).first()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="구독을 찾을 수 없습니다."
            )
        
        # 구독 상세 정보 반환 (실제 구현 필요)
        return SubscriptionResponse(
            id=subscription.id,
            user_uuid=subscription.user_uuid,
            plan_id=subscription.plan_id,
            plan_name="Plan Name",
            status=subscription.status,
            start_date=subscription.start_date.isoformat(),
            end_date=subscription.end_date.isoformat(),
            auto_renewal=subscription.auto_renewal
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 상세 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="구독 조회 중 오류가 발생했습니다."
        )

@router.put("/{subscription_id}", summary="구독 수정")
async def update_subscription(
    subscription_id: int,
    auto_renewal: bool,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    구독 설정을 수정합니다.
    
    - **auto_renewal**: 자동 갱신 여부
    """
    logger.info(f"🔧 구독 수정 - ID: {subscription_id}, 사용자: {current_user}")
    
    try:
        # 구독 조회 및 권한 확인
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.id == subscription_id,
            SubscriptionMaster.user_uuid == current_user
        ).first()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="구독을 찾을 수 없습니다."
            )
        
        # 구독 수정 로직 (실제 구현 필요)
        # update_subscription_settings(subscription, auto_renewal, db)
        
        logger.info(f"✅ 구독 수정 완료 - ID: {subscription_id}")
        return {
            "status": "success",
            "message": "구독이 성공적으로 수정되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 수정 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="구독 수정 중 오류가 발생했습니다."
        )

@router.post("/{subscription_id}/change", summary="구독 변경")
async def change_subscription(
    subscription_id: int,
    change_data: SubscriptionChange,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    구독 요금제를 변경합니다.
    
    - **new_plan_id**: 변경할 요금제 ID
    - **change_type**: 변경 유형 (upgrade, downgrade, change)
    - **effective_date**: 변경 적용일 (선택사항)
    """
    logger.info(f"🔄 구독 변경 - ID: {subscription_id}, 새 요금제: {change_data.new_plan_id}")
    
    try:
        # 구독 조회 및 권한 확인
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.id == subscription_id,
            SubscriptionMaster.user_uuid == current_user
        ).first()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="구독을 찾을 수 없습니다."
            )
        
        # 새 요금제 존재 확인
        new_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == change_data.new_plan_id).first()
        if not new_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="새 요금제를 찾을 수 없습니다."
            )
        
        # 구독 변경 로직 (실제 구현 필요)
        # change_subscription_plan(subscription, change_data, db)
        
        logger.info(f"✅ 구독 변경 완료 - ID: {subscription_id}")
        return {
            "status": "success",
            "message": "구독이 성공적으로 변경되었습니다.",
            "change_type": change_data.change_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 변경 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="구독 변경 중 오류가 발생했습니다."
        )

@router.get("/{subscription_id}/history", summary="구독 이력 조회")
async def get_subscription_history(
    subscription_id: int,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    구독의 변경 이력을 조회합니다.
    """
    logger.info(f"📋 구독 이력 조회 - ID: {subscription_id}, 사용자: {current_user}")
    
    try:
        # 구독 조회 및 권한 확인
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.id == subscription_id,
            SubscriptionMaster.user_uuid == current_user
        ).first()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="구독을 찾을 수 없습니다."
            )
        
        # 구독 이력 조회 로직 (실제 구현 필요)
        # history = get_subscription_history_from_db(subscription_id, db)
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 이력 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="구독 이력 조회 중 오류가 발생했습니다."
        )

# 구독 요금제 관련 엔드포인트
@router.get("/plans/", summary="구독 요금제 목록")
async def get_subscription_plans(
    db: Session = Depends(get_db),
    active_only: bool = Query(True, description="활성 요금제만 조회")
) -> List[SubscriptionPlanResponse]:
    """
    사용 가능한 구독 요금제 목록을 조회합니다.
    
    - **active_only**: 활성 요금제만 조회할지 여부
    """
    logger.info(f"📋 구독 요금제 목록 조회 - 활성만: {active_only}")
    
    try:
        # 요금제 목록 조회 로직 (실제 구현 필요)
        # plans = get_subscription_plans_from_db(active_only, db)
        
        return []
        
    except Exception as e:
        logger.error(f"❌ 요금제 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="요금제 목록 조회 중 오류가 발생했습니다."
        )