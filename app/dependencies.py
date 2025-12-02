# app/dependencies.py
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .auth_utils import decode_access_token, oauth2_scheme
from .database import get_db

# استخدام Annotated مع Depends لتحديد النوع بوضوح
DatabaseDependency = Annotated[Session, Depends(get_db)]
TokenDependency = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(
    db: DatabaseDependency, token: TokenDependency
) -> models.User:
    """الحصول على المستخدم الحالي من رمز JWT والتحقق من صلاحيته"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="تعذر التحقق من بيانات الاعتماد",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. فك ترميز التوكن
    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exception

    user_email = token_data.get("email")
    if user_email is None:
        raise credentials_exception

    # 2. جلب المستخدم من قاعدة البيانات
    user = crud.get_user_by_email(db, email=user_email)
    if user is None:
        raise credentials_exception

    return user


# يمكن تعريف اختصار لـ get_current_user
# Expose the actual callable so routes that do Depends(ActiveUser) work correctly.
# Previously ActiveUser was an Annotated type which caused FastAPI to treat it
# incorrectly and attempt to parse query params like 'args'/'kwargs'.
ActiveUser = get_current_user
