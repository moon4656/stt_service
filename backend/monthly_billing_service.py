from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid
import logging

from app import get_last_day_of_month
from database import (
    MonthlyBilling, TokenUsageHistory, ServiceToken, SubscriptionMaster,
    Payment, SubscriptionPayment, OveragePayment, SubscriptionPlan,
    User, get_db
)

# 로거 설정
logger = logging.getLogger(__name__)

class MonthlyBillingService:
    """월빌링 서비스 클래스 - 월별 사용량 집계 및 청구서 생성을 담당합니다."""
    
    def __init__(self, db: Session):
        """월빌링 서비스 초기화
        
        Args:
            db: 데이터베이스 세션
        """
        self.db = db
        self.kst = timezone(timedelta(hours=9))  # 한국 시간대
    
    # 월빌링 생성
    def generate_monthly_billing(self, target_year: int, target_month: int) -> Dict[str, any]:
        """월빌링 생성 - 지정된 년월의 모든 사용자에 대한 월빌링을 생성합니다.
        
        Args:
            target_year: 청구 연도
            target_month: 청구 월
            
        Returns:
            생성 결과 딕셔너리
        """
        logger.info(f"🚀 월빌링 생성 시작 - {target_year}년 {target_month}월")
        
        try:
            # 청구 기간 설정
            billing_start = date(target_year, target_month, 1)
            if target_month == 12:
                billing_end = date(target_year + 1, 1, 1) - timedelta(days=1)
            else:
                billing_end = date(target_year, target_month + 1, 1) - timedelta(days=1)
            
            logger.info(f"✅ 청구 기간: {billing_start} ~ {billing_end}")
            
            # 활성 구독이 있는 모든 사용자 조회
            active_subscriptions = self.db.query(SubscriptionMaster).filter(
                SubscriptionMaster.subscription_status == 'active'
            ).all()
            
            created_billings = []
            
            for subscription in active_subscriptions:
                
                logger.info(f" subscription loop: user_uuid={subscription.user_uuid}, plan_id={subscription.plan_code}")
                try:
                    # 사용자별 월빌링 생성
                    logger.info(f" subscription: user_uuid={subscription.user_uuid}, {target_year}, {target_month}, {billing_start}, {billing_end}")
                    billing = self._create_user_monthly_billing(
                        subscription, target_year, target_month, billing_start, billing_end
                    )
                    
                    logger.info(f"✅ 사용자 {billing} ")
                    
                    if billing:
                        created_billings.append(billing)
                        
                except Exception as e:
                    logger.error(f"❌ 사용자 {subscription.user_uuid} 월빌링 생성 실패: {str(e)}")
                    continue
            
            self.db.commit()
            
            result = {
                "status": "success",
                "message": f"{target_year}년 {target_month}월 월빌링 생성 완료",
                "created_count": len(created_billings),
                "billing_period": f"{billing_start} ~ {billing_end}",
                "billings": [{
                    "user_uuid": b.user_uuid,
                    "total_amount": b.total_billing_amount,
                    "excess_amount": b.excess_usage_fee
                } for b in created_billings]
            }
            
            logger.info(f"✅ 월빌링 생성 완료 - 총 {len(created_billings)}건")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ 월빌링 생성 실패: {str(e)}")
            raise
    
    def _create_user_monthly_billing(self, subscription: SubscriptionMaster, 
                                   target_year: int, 
                                   target_month: int,
                                   billing_start: date, 
                                   billing_end: date) -> Optional[MonthlyBilling]:
        """사용자별 월빌링 생성
        
        Args:
            subscription: 구독 정보
            target_year: 청구 연도
            target_month: 청구 월
            billing_start: 청구 기간 시작일
            billing_end: 청구 기간 종료일
            
        Returns:
            생성된 월빌링 객체 또는 None
        """
        user_uuid = subscription.user_uuid

        logger.info(f" 🔍 사용자 {user_uuid}의 {target_year}년 {target_month}월 월빌링 생성 시작")
        
        # 이미 해당 월 빌링이 존재하는지 확인
        existing_billing = self.db.query(MonthlyBilling).filter(
            and_(
                MonthlyBilling.user_uuid == user_uuid,
                MonthlyBilling.billing_year == target_year,
                MonthlyBilling.billing_month == target_month
            )
        ).first()
        
        if existing_billing:
            logger.warning(f"⚠️ 사용자 {user_uuid}의 {target_year}년 {target_month}월 빌링이 이미 존재합니다.")
            return None
        
        # 요금제 정보 조회
        plan = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_code == subscription.plan_code
        ).first()
        
        if not plan:
            logger.error(f"❌ 요금제 {subscription.plan_code}를 찾을 수 없습니다.")
            return None
        
        # 월별 사용량 집계
        usage_stats = self._calculate_monthly_usage(user_uuid, billing_start, billing_end)
        
        logger.info(f"✅ 사용자 {user_uuid} 월별 사용량 집계: {usage_stats}")
        
        # Get subscription quota tokens from service_tokens
        service_token = self.db.query(ServiceToken).filter(
            ServiceToken.user_uuid == user_uuid
        ).first()
        
        if not service_token:
            logger.warning(f"⚠️ No service token found for user {user_uuid}")
            quota_tokens = 0
        else:
            logger.info(f" service_token.quota_tokens: {service_token.quota_tokens}")
            quota_tokens = float(service_token.quota_tokens or 0)

        logger.info(f" service_token.quota_tokens: {service_token.quota_tokens}, quota_tokens: {quota_tokens}")
            
        logger.info(f"✅ User {user_uuid} quota tokens: {quota_tokens} usage_stats['total_minutes']: {usage_stats['total_minutes']}")
        
        # 초과 사용량 계산
        excess_minutes = max(0, usage_stats['total_minutes'] - quota_tokens)
        
        # 요금 계산
        base_fee = subscription.amount  # 기본 구독료
        excess_fee = int(excess_minutes * (plan.overage_per_minute_rate or 0))  # 초과 사용료
        subtotal = base_fee + excess_fee
        vat = int(subtotal * 0.1)  # 부가세 10%
        total_amount = subtotal + vat
        
        # 월빌링 생성
        billing = MonthlyBilling(
            user_uuid=user_uuid,
            billing_year=target_year,
            billing_month=target_month,
            plan_code=subscription.plan_code,
            total_minutes_used=usage_stats['total_minutes'],
            included_minutes=quota_tokens,
            excess_minutes=excess_minutes,
            total_requests=usage_stats['total_requests'],
            base_subscription_fee=base_fee,
            per_minute_rate=plan.per_minute_rate,
            excess_per_minute_rate=plan.overage_per_minute_rate,
            excess_usage_fee=excess_fee,
            subtotal_amount=subtotal,
            vat_amount=vat,
            total_billing_amount=total_amount,
            billing_status='pending',
            payment_due_date=billing_end + timedelta(days=30),  # 청구서 발행 후 30일
            paid_at=datetime.now(self.kst),
            billing_period_start=billing_start,
            billing_period_end=billing_end
        )
        
        self.db.add(billing)
        
        logger.info(f"📊 _create_user_monthly_billing ---------------------------------------------------1")
        
        # 초과 사용량이 있는 경우 초과 결제 처리
        if excess_minutes > 0:
            self._process_overage_payment(user_uuid, subscription.plan_code, excess_minutes, excess_fee)
        
        logger.info(f"📊 사용자 {user_uuid} 월빌링 생성 - 총액: {total_amount:,}원 (초과: {excess_fee:,}원)")
        return billing
    
    # 월별 사용량월별 사용량 집계 집계
    def _calculate_monthly_usage(self, user_uuid: str, start_date: date, end_date: date) -> Dict[str, float]:
        """월별 사용량 집계
        /
        Args:
            user_uuid: 사용자 UUID
            start_date: 집계 시작일
            end_date: 집계 종료일
            
        Returns:
            사용량 통계 딕셔너리
        """
        # 토큰 사용 내역에서 월별 사용량 집계
        usage_query = self.db.query(
            func.sum(TokenUsageHistory.used_tokens).label('total_tokens'),
            func.count(TokenUsageHistory.id).label('total_requests')
        ).filter(
            and_(
                TokenUsageHistory.user_uuid == user_uuid,
                func.date(TokenUsageHistory.created_at) >= start_date,
                func.date(TokenUsageHistory.created_at) <= end_date
            )
        ).first()
        
        total_tokens = float(usage_query.total_tokens or 0)
        total_requests = int(usage_query.total_requests or 0)
        
        return {
            'total_minutes': total_tokens,  # 토큰 = 분 단위
            'total_requests': total_requests
        }
    
    # 초과 사용량 결제 처리
    def _process_overage_payment(self, user_uuid: str, plan_code: str, 
                               excess_minutes: float, excess_fee: int) -> None:
        """초과 사용량 결제 처리
        
        Args:
            user_uuid: 사용자 UUID
            plan_code: 요금제 코드
            excess_minutes: 초과 사용 시간(분)
            excess_fee: 초과 사용료
        """
        try:
            # 결제 마스터 생성
            payment_id = f"PAY-{datetime.now(self.kst).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            
            payment = Payment(
                payment_id=payment_id,
                user_uuid=user_uuid,
                plan_code=plan_code,
                supply_amount=excess_fee,
                vat_amount=int(excess_fee * 0.1),
                total_amount=int(excess_fee * 1.1),
                payment_method='auto',  # 자동 결제
                payment_status='pending'
            )
            self.db.add(payment)
            
            # 초과 결제 상세 생성
            plan = self.db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_code == plan_code
            ).first()
            
            overage_payment = OveragePayment(
                payment_id=payment_id,
                plan_code=plan_code,
                unit_price=plan.per_minute_rate or 0,
                overage_unit_price=plan.overage_per_minute_rate or 0,
                overage_tokens=excess_minutes,
                amount=excess_fee
            )
            self.db.add(overage_payment)
            
            logger.info(f"💳 초과 결제 생성 - 사용자: {user_uuid}, 금액: {excess_fee:,}원")
            
        except Exception as e:
            logger.error(f"❌ 초과 결제 처리 실패: {str(e)}")
            raise
    
    # 월구독결제 생성
    # 월 구독료 결제를 생성합니다.
    # 서비스 토큰 초기화
    def create_monthly_subscription_billing(self, target_year: int, target_month: int) -> Dict[str, any]:
        """월구독결제 생성 - 활성 구독자들의 월 구독료 결제를 생성합니다.
        
        Args:
            target_year: 결제 연도
            target_month: 결제 월
            
        Returns:
            생성 결과 딕셔너리
        """
        logger.info(f"🚀 월구독결제 생성 시작 - {target_year}년 {target_month}월")

        last_day = get_last_day_of_month(target_year, target_month)        
       
        try:
            # 활성 구독 조회
            active_subscriptions = self.db.query(SubscriptionMaster).filter(
                SubscriptionMaster.subscription_status == 'active'
            ).all()
            
            created_payments = []
            
            for subscription in active_subscriptions:
                try:
                    # 결제, 구독결제상세 생성
                    payment_result = self._create_subscription_payment(subscription, target_year, target_month)
                    if payment_result:
                        created_payments.append(payment_result)
                        
                        # 서비스 토큰 초기화
                        self._reset_service_tokens(subscription, last_day)
                        
                        # 구독 마스터 업데이트
                        subscription.subscription_status = 'active'
                        subscription.subscription_start_date = datetime(target_year, target_month, 1)
                        subscription.subscription_end_date = last_day 
                        subscription.next_billing_date = last_day + timedelta(days=1)
                        
                except Exception as e:
                    logger.error(f"❌ 사용자 {subscription.user_uuid} 구독결제 생성 실패: {str(e)}")
                    continue
            
            self.db.commit()
            
            result = {
                "status": "success",
                "message": f"{target_year}년 {target_month}월 구독결제 생성 완료",
                "created_count": len(created_payments),
                "payments": created_payments
            }
            
            logger.info(f"✅ 월구독결제 생성 완료 - 총 {len(created_payments)}건")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ 월구독결제 생성 실패: {str(e)}")
            raise
    
    # 구독 결제 생성
    def _create_subscription_payment(self, subscription: SubscriptionMaster, 
                                   target_year: int, target_month: int) -> Optional[Dict[str, any]]:
        """구독 결제 생성
        
        Args:
            subscription: 구독 정보
            target_year: 결제 연도
            target_month: 결제 월
            
        Returns:
            생성된 결제 정보 딕셔너리 또는 None
        """
        try:
            # 결제 ID 생성
            payment_id = f"SUB-{datetime.now(self.kst).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            
            # 결제 마스터 생성
            payment = Payment(
                payment_id=payment_id,
                user_uuid=subscription.user_uuid,
                plan_code=subscription.plan_code,
                supply_amount=subscription.amount,
                vat_amount=int(subscription.amount * 0.1),
                total_amount=int(subscription.amount * 1.1),
                payment_method='auto',
                payment_status='completed',  # 구독료는 자동 결제 완료로 처리
                completed_at=datetime.now(self.kst)
            )
            self.db.add(payment)
            
            # 구독 결제 상세 생성
            subscription_payment = SubscriptionPayment(
                payment_id=payment_id,
                plan_code=subscription.plan_code,
                unit_price=subscription.amount,
                quantity=subscription.quantity,
                amount=subscription.amount
            )
            self.db.add(subscription_payment)
            
            logger.info(f"💳 구독결제 생성 - 사용자: {subscription.user_uuid}, 금액: {subscription.amount:,}원")
            
            return {
                "payment_id": payment_id,
                "user_uuid": subscription.user_uuid,
                "plan_code": subscription.plan_code,
                "amount": subscription.amount
            }
            
        except Exception as e:
            logger.error(f"❌ 구독결제 생성 실패: {str(e)}")
            return None
    
    def _reset_service_tokens(self, subscription: SubscriptionMaster, last_day: date) -> None:
        """서비스 토큰 초기화 - 월 구독 결제 후 토큰을 리셋합니다.
        
        Args:
            user_uuid: 사용자 UUID
            plan_code: 요금제 코드
        """
        try:
            # 요금제 정보 조회
            plan = self.db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_code == subscription.plan_code
            ).first()
            
            if not plan:
                logger.error(f"❌ 요금제 {subscription.plan_code}를 찾을 수 없습니다.")
                return
            
            # 기존 서비스 토큰 조회
            service_token = self.db.query(ServiceToken).filter(
                ServiceToken.user_uuid == subscription.user_uuid
            ).first()
            
            quota_tokens = plan.monthly_service_tokens *subscription.quantity
            
            if service_token:
                # 기존 토큰 업데이트
                service_token.quota_tokens = Decimal(str(quota_tokens or 0))
                service_token.used_tokens = Decimal('0.0')
                service_token.token_expiry_date = last_day
                service_token.status = 'active'
                service_token.updated_at = datetime.now(self.kst)
            
            else:
                # 새 토큰 생성
                service_token = ServiceToken(
                    user_uuid=subscription.user_uuid,
                    quota_tokens=Decimal(str(quota_tokens or 0)),
                    used_tokens=Decimal('0.0'),
                    token_expiry_date=last_day,
                    status='active'
                )
                self.db.add(service_token)
            
            logger.info(f"🔄 서비스토큰 초기화 - 사용자: {subscription.user_uuid}, 할당토큰: {quota_tokens}분")
            
        except Exception as e:
            logger.error(f"❌ 서비스토큰 초기화 실패: {str(e)}")
            raise
    
    def get_monthly_billing_summary(self, target_year: int, target_month: int) -> Dict[str, any]:
        """월빌링 요약 조회
        
        Args:
            target_year: 조회 연도
            target_month: 조회 월
            
        Returns:
            월빌링 요약 정보
        """
        try:
            # 월빌링 통계 조회
            billing_stats = self.db.query(
                func.count(MonthlyBilling.id).label('total_billings'),
                func.sum(MonthlyBilling.total_billing_amount).label('total_amount'),
                func.sum(MonthlyBilling.excess_usage_fee).label('total_excess_fee'),
                func.avg(MonthlyBilling.total_minutes_used).label('avg_usage_minutes')
            ).filter(
                and_(
                    MonthlyBilling.billing_year == target_year,
                    MonthlyBilling.billing_month == target_month
                )
            ).first()
            
            # 상태별 빌링 수 조회
            status_stats = self.db.query(
                MonthlyBilling.billing_status,
                func.count(MonthlyBilling.id).label('count')
            ).filter(
                and_(
                    MonthlyBilling.billing_year == target_year,
                    MonthlyBilling.billing_month == target_month
                )
            ).group_by(MonthlyBilling.billing_status).all()
            
            return {
                "period": f"{target_year}년 {target_month}월",
                "total_billings": int(billing_stats.total_billings or 0),
                "total_amount": int(billing_stats.total_amount or 0),
                "total_excess_fee": int(billing_stats.total_excess_fee or 0),
                "avg_usage_minutes": float(billing_stats.avg_usage_minutes or 0),
                "status_breakdown": {status: count for status, count in status_stats}
            }
            
        except Exception as e:
            logger.error(f"❌ 월빌링 요약 조회 실패: {str(e)}")
            raise


def create_monthly_billing_for_current_month(db: Session) -> Dict[str, any]:
    """현재 월의 월빌링을 생성합니다.
    
    Args:
        db: 데이터베이스 세션
        
    Returns:
        생성 결과 딕셔너리
    """
    service = MonthlyBillingService(db)
    now = datetime.now(service.kst)
    return service.generate_monthly_billing(now.year, now.month)


def create_subscription_payments_for_current_month(db: Session) -> Dict[str, any]:
    """현재 월의 구독결제를 생성합니다.
    
    Args:
        db: 데이터베이스 세션
        
    Returns:
        생성 결과 딕셔너리
    """
    service = MonthlyBillingService(db)
    now = datetime.now(service.kst)
    return service.create_monthly_subscription_billing(now.year, now.month)

def get_last_day_of_month(year: int, month: int) -> date:
    """Get the last day of the given year and month
    
    Args:
        year: Target year
        month: Target month
        
    Returns:
        Date object representing the last day of month
    """
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    else:
        return date(year, month + 1, 1) - timedelta(days=1)
# 사용 예시
if __name__ == "__main__":
    # 데이터베이스 세션 생성
    """
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        # 월빌링 서비스 생성
        # service = MonthlyBillingService(db)
        
        # 현재 월 빌링 생성 create_monthly_billing_for_current_month
        result = create_monthly_billing_for_current_month(db)
        print(f"월빌링 생성 결과: {result}")
        
        # 현재 월 구독결제 생성
        payment_result = create_subscription_payments_for_current_month(db)
        print(f"구독결제 생성 결과: {payment_result}")
        
    finally:
        db.close()
    """