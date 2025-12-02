# app/routers/subscriptions.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..dependencies import get_current_user, get_db

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"],
)

@router.post("/activate", response_model=schemas.UserRead)
def activate_subscription(
    activation_data: schemas.ActivationCodeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    print(f"Received activation request with data: {activation_data}")
    """
    Activates a subscription for the current user using a file-based activation code.
    """
    code_to_activate = activation_data.code

    # Use the code from the database. This is an atomic operation.
    plan_type = crud.use_activation_code(db, code=code_to_activate, user_id=current_user.id)

    if plan_type == "not_found":
        raise HTTPException(
            status_code=404,
            detail="ACTIVATION_CODE_NOT_FOUND",
        )
    
    if plan_type == "already_used":
        raise HTTPException(
            status_code=400,
            detail="ACTIVATION_CODE_ALREADY_USED",
        )

    if not plan_type:
        raise HTTPException(
            status_code=400,
            detail="ACTIVATION_CODE_INVALID",
        )

    # Update the user's subscription status
    expires_at = None
    if plan_type == "weekly":
        expires_at = datetime.utcnow() + timedelta(weeks=1)
    elif plan_type == "monthly":
        expires_at = datetime.utcnow() + timedelta(days=30)
    elif plan_type == "yearly":
        expires_at = datetime.utcnow() + timedelta(days=365)
    elif plan_type == "lifetime":
        expires_at = None  # Or a very far future date

    subscription_data = schemas.SubscriptionUpdate(
        plan=plan_type,
        is_premium=True,
        expires_at=expires_at,
    )
    updated_user = crud.update_subscription(db, user_id=current_user.id, subscription=subscription_data)

    return updated_user