# app/auth_utils.py 

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

# --- إعدادات JWT (بدون تغيير) ---
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """التحقق من كلمة المرور العادية مقابل المجزأة"""
    # لا نحتاج لتقييد الطول هنا
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """تجزئة كلمة المرور"""
    # لا نحتاج لتقييد الطول هنا
    return pwd_context.hash(password)


# --- وظائف JWT (بدون تغيير) ---


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # JWT 'exp' should be a numeric timestamp (seconds since epoch).
    # Some JWT libraries (and JSON serialization) fail when given a datetime object.
    exp_timestamp = int(expire.timestamp())
    to_encode.update({"exp": exp_timestamp, "sub": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
