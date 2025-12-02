# app/database.py
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. تحميل متغيرات البيئة
load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables.")

# 2. إنشاء محرك الاتصال
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# 3. إنشاء فئة جلسة العمل
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. إنشاء الكلاس الأساسي لنماذج SQLAlchemy
Base = declarative_base()


# 5. دالة للحصول على جلسة قاعدة البيانات (Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
