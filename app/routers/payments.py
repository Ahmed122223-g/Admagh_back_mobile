# app/routers/payments.py
import os
import httpx  
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..dependencies import get_current_user, get_db

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)

# مفاتيح Kashier - يتم تحميلها مرة واحدة من متغيرات البيئة
KASHIER_MERCHANT_ID = os.getenv("KASHIER_MERCHANT_ID")
KASHIER_API_KEY = os.getenv("KASHIER_API_KEY")


@router.post("/kashier/create-payment-link")
async def create_kashier_payment_link(payload: dict):
    """
    نقطة نهاية لإنشاء رابط الدفع من كاشير وتحويل المستخدم إليه.
    """
    # 1. التحقق من مفاتيح الخادم
    if not KASHIER_MERCHANT_ID or not KASHIER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kashier credentials are not set on server. Please check .env file.",
        )

    # 2. استخلاص بيانات الدفع من الواجهة الأمامية
    amount = payload.get("amount")
    currency = payload.get("currency", "EGP")
    merchant_order_id = payload.get("merchant_order_id")

    if not all([amount, merchant_order_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount and merchant_order_id are required",
        )

    # 3. إعداد الطلب إلى Kashier
    url = "https://api.kashier.io/v1/payment-requests"

    headers = {
        "Authorization": KASHIER_API_KEY,  # المفتاح السري
        "Content-Type": "application/json",
    }

    data = {
        "merchantId": KASHIER_MERCHANT_ID,
        "amount": amount,
        "currency": currency,
        "orderId": merchant_order_id,
        "redirectUrl": "http://localhost:5173/dashboard",  # المسار الذي يعود إليه المستخدم بعد الدفع
        "display": "ar",  # استخدام اللغة العربية
    }

    # 4. إرسال الطلب بشكل غير متزامن
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            # معالجة الأخطاء الواردة من Kashier (مثل مفاتيح خاطئة)
            print(f"Kashier API Error: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Kashier Error: {e.response.text}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to Kashier: {e}",
            )

    # 5. إعادة رابط الدفع إلى الواجهة الأمامية
    return response.json()


@router.post("/kashier/webhook")
async def kashier_webhook(request: Request):
    """
    نقطة نهاية استقبال إشعارات الـ Webhook من كاشير.
    يجب إضافة منطق التحقق من التوقيع (HMAC verification) هنا.
    """
    data = await request.json()
    print(f"Kashier webhook received: {data}")
    return {"status": "ok"}



