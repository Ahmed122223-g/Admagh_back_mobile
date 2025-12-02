# app/routers/auth.py
from datetime import datetime, timedelta
from typing import Annotated, Optional



import random
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
import traceback
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import exc
from fastapi_mail import MessageSchema, MessageType

from .. import crud, schemas
from ..auth_utils import create_access_token, get_password_hash, verify_password
from ..database import get_db
from ..dependencies import ActiveUser
from ..email_utils import fm, send_verification_code_email
import firebase_admin
from firebase_admin import auth, exceptions

router = APIRouter(
    prefix="/auth",
    tags=["المصادقة (Auth)"],
)

class FCMTokenRequest(BaseModel):
    token: str

@router.post("/users/me/fcm-token", status_code=status.HTTP_200_OK)
def update_fcm_token(
    token_request: FCMTokenRequest,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """Update the FCM token for the current user."""
    crud.update_user_fcm_token(db, user_id=current_user.id, fcm_token=token_request.token)
    return {"message": "FCM token updated successfully."}

@router.post("/firebase-login", response_model=schemas.Token)
async def firebase_login(
    firebase_request: schemas.FirebaseTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with Firebase ID token and return a custom JWT.
    If the user doesn't exist in our DB, create them.
    """
    try:
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(firebase_request.id_token)
        firebase_uid = decoded_token["uid"]
        email = decoded_token.get("email")
        name = decoded_token.get("name", email.split('@')[0] if email else "Firebase User") # Default name if not provided by Firebase

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Firebase token does not contain an email address."
            )

        # Get or create user in our database
        user = crud.get_or_create_user_by_firebase_uid(db, firebase_uid, email, name)

        # Generate our own JWT for the user
        access_token = create_access_token(data={"email": user.email, "user_id": user.id})

        return schemas.Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Firebase ID token: {e}"
        )
    except exceptions.FirebaseError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Firebase authentication failed: {e}"
        )
    except Exception as e:
        tb = traceback.format_exc()
        print(f"ERROR during Firebase login: {tb}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during Firebase login: {e}"
        )

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a 6-digit password reset code."""
    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with that email does not exist.",
        )
    
    code = crud.generate_password_reset_code(db, email=request.email)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate reset code.",
        )

    message = MessageSchema(
        subject="Password Reset Code",
        recipients=[request.email],
        body=f"Your password reset code is: <b>{code}</b>. It is valid for 10 minutes.",
        subtype=MessageType.html,
    )

    await fm.send_message(message)
    return {"message": "Password reset code sent to your email."}


@router.post("/verify-code", status_code=status.HTTP_200_OK)
def verify_code(request: schemas.VerifyResetCode, db: Session = Depends(get_db)):
    """Verify the 6-digit password reset code."""
    user = crud.verify_password_reset_code(db, email=request.email, code=request.code)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code.",
        )
    return {"message": "Code verified successfully."}


@router.post("/reset-password-confirm", status_code=status.HTTP_200_OK)
def reset_password_confirm(request: schemas.ResetPasswordConfirm, db: Session = Depends(get_db)):
    """Reset user's password after code verification."""
    user = crud.verify_password_reset_code(db, email=request.email, code=request.code)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code.",
        )
    crud.reset_user_password(db, user=user, new_password=request.new_password)
    return {"message": "Password has been reset successfully."}


@router.post(
    "/signup", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED
)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """إنشاء حساب مستخدم جديد وإرسال كود تفعيل"""
    if crud.get_user_by_email(db, email=user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الإلكتروني مستخدم بالفعل",
        )
    
    try:
        # Create user in local DB and Firebase
        new_user = crud.create_user(db=db, user=user)

        # Generate 6-digit verification code
        code = str(random.randint(100000, 999999))
        
        # Store code in the database
        new_user.email_verification_code = code
        new_user.email_verification_code_expires_at = None
        db.commit()
        db.refresh(new_user)

        # Send verification email with the code
        await send_verification_code_email(email=new_user.email, name=new_user.name, code=code)

        return new_user

    except HTTPException:
        # Re-raise HTTPException as-is
        db.rollback()
        raise
    except exceptions.FirebaseError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating user in Firebase: {e}")
    except Exception as e:
        db.rollback()
        tb = traceback.format_exc()
        print(f"ERROR during signup: {tb}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )


@router.post("/verify-email-code", response_model=schemas.Token)
async def verify_email_code(request: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with a 6-digit code and return a JWT token."""
    user = crud.get_user_by_email(db, email=request.email)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    if user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified.")

    if (
        not user.email_verification_code
        or user.email_verification_code != request.code.strip()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code.")

    # --- Verification successful ---
    user.is_verified = True
    user.email_verification_code = None
    user.email_verification_code_expires_at = None
    
    # Also update the user in Firebase if they have a firebase_uid
    if user.firebase_uid:
        try:
            auth.update_user(user.firebase_uid, email_verified=True)
        except exceptions.FirebaseError as e:
            # This is not critical enough to fail the whole process, but should be logged.
            print(f"Warning: Could not set email_verified in Firebase for user {user.firebase_uid}: {e}")

    db.commit()

    # Create access token for immediate login
    access_token = create_access_token(data={"email": user.email, "user_id": user.id})
    return schemas.Token(access_token=access_token, token_type="bearer")


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """تسجيل دخول المستخدم وإصدار رمز JWT"""
    user = crud.get_user_by_email(db, email=form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الالكتروني او كلمه المرور غير صحيحه",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الإلكتروني غير مؤكد. يرجى التحقق من بريدك الإلكتروني.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"email": user.email, "user_id": user.id})

    return schemas.Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=schemas.UserRead)
def read_current_user(current_user: schemas.UserRead = Depends(ActiveUser)):
    """Return current authenticated user's profile"""
    return current_user


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    passwords: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """تغيير كلمة مرور المستخدم الحالي"""
    user = crud.get_user_by_email(db, email=current_user.email)
    if not user or not verify_password(passwords.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمة المرور القديمة غير صحيحة",
        )

    hashed_password = get_password_hash(passwords.new_password)
    user.hashed_password = hashed_password
    db.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router.delete("/delete-account", status_code=status.HTTP_200_OK)
def delete_account(
    email: str,  # Email for confirmation
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """حذف حساب المستخدم الحالي وجميع بياناته بشكل دائم"""
    if current_user.email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الإلكتروني غير متطابق. يرجى تأكيد بريدك الإلكتروني.",
        )

    if not crud.delete_user(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="فشل حذف الحساب."
        )

    return {"message": "تم حذف الحساب بنجاح."}


class UpdateNameRequest(BaseModel):
    new_name: str


@router.patch("/users/me/name", response_model=schemas.UserRead)
def update_user_name(
    name_request: UpdateNameRequest,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """
    Update user's name with 30-day restriction.
    Users can only change their name once every 30 days.
    """
    user = crud.get_user(db, current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود"
        )
    
    # Check if user has changed name before and if 30 days have passed
    # Only if the column exists
    try:
        if hasattr(user, 'last_name_change') and user.last_name_change:
            days_since_last_change = (datetime.utcnow() - user.last_name_change).days
            if days_since_last_change < 30:
                days_remaining = 30 - days_since_last_change
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"NAME_CHANGE_RESTRICTED|{days_remaining}"
                )
    except AttributeError:
        # Column doesn't exist, allow change
        pass
    
    # Update name
    user.name = name_request.new_name.strip()
    
    # Update last_name_change if column exists
    try:
        if hasattr(user, 'last_name_change'):
            user.last_name_change = datetime.utcnow()
    except AttributeError:
        pass
    
    db.commit()
    db.refresh(user)
    
    return user
