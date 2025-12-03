# app/models.py
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,String, Text, BigInteger, Enum, func, Date, JSON)
from sqlalchemy.orm import relationship

from .database import Base


# --- نموذج المستخدم (User) ---
class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=False)
    firebase_uid = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    fcm_token = Column(String, nullable=True)
    is_unlocked = Column(Boolean, default=False)
    plan = Column(String, nullable=True)
    subscription_id = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_premium = Column(Boolean, default=False)  
    premium_plan = Column(String, nullable=True)  
    created_at = Column(DateTime, server_default=func.now())
    reset_password_token = Column(String, nullable=True)
    reset_password_token_expires = Column(DateTime, nullable=True)
    reset_password_code = Column(String, nullable=True) # New field for 6-digit code
    reset_password_code_expires = Column(DateTime, nullable=True) # New field for code expiration
    email_verification_code = Column(String, nullable=True)
    email_verification_code_expires_at = Column(DateTime, nullable=True)
    last_name_change = Column(DateTime, nullable=True)  # Track last time user changed their name
    profile_picture = Column(String, nullable=True)  # URL or path to profile picture
    
    # Challenge Stats
    gold_cups = Column(Integer, default=0)
    silver_cups = Column(Integer, default=0)
    bronze_cups = Column(Integer, default=0)
    challenges_count = Column(Integer, default=0)

    tasks = relationship("Task", back_populates="owner")
    notes = relationship("Note", back_populates="owner")
    friendships_sent = relationship("Friendship", foreign_keys="[Friendship.user_id]", back_populates="user")
    friendships_received = relationship("Friendship", foreign_keys="[Friendship.friend_id]", back_populates="friend")
    
    
    habits = relationship("Habit", back_populates="user")
  



# --- Task Feature Models ---
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"))
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    priority = Column(String, default="متوسطة")
    status = Column(String, default="لم تبدأ")
    due_date = Column(DateTime)
    category = Column(String, default="عام")
    completed = Column(Boolean, default=False)
    estimated_hours = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)
    start_time = Column(DateTime, nullable=True)
    remaining_time_seconds = Column(Integer, default=0, nullable=False)
    time_spent_seconds = Column(Integer, default=0, nullable=False)
    initial_duration_seconds = Column(Integer, default=3600, nullable=False)
    last_run_date = Column(DateTime, nullable=True)
    progress_details = Column(Text, nullable=True)
    owner = relationship("User", back_populates="tasks")

# --- Note Feature Models ---
class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"))
    title = Column(String)
    content = Column(Text)
    category = Column(String, default="أفكار")
    is_starred = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="notes")

# --- Activation Code Feature Models ---
class ActivationCode(Base):
    __tablename__ = "activation_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    plan_type = Column(String, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    used_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    used_by = relationship("User")

# --- Friendship Feature Models ---
class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    friend_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    status = Column(String, default="pending") # "pending", "accepted", "rejected"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])


# --- Custom Calendar System ---
class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)  # Now nullable
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=True)  # New field
    event_type = Column(String(20), nullable=False, default='task', index=True)  # 'task' or 'habit'
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notification_sent = Column(Boolean, default=False)
    
    user = relationship("User")
    task = relationship("Task")
    habit = relationship("Habit", back_populates="calendar_events")


# --- Habit Model ---
class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Type
    is_permanent = Column(Boolean, nullable=False, default=True, index=True)
    frequency = Column(String(20), nullable=False, index=True)  # 'daily', 'weekly', 'monthly'
    
    # Duration
    duration_minutes = Column(Integer, nullable=False, default=30)
    
    # Daily habits
    repetitions_per_day = Column(Integer)
    daily_times = Column(JSON)  # List of {hour, minute}
    
    # Weekly habits
    weekly_days = Column(JSON)  # List of day names/numbers
    weekly_times = Column(JSON)  # List of {day, hour, minute}
    
    # Monthly habits
    repetitions_per_month = Column(Integer)
    monthly_days = Column(JSON)  # List of day numbers (1-31)
    monthly_times = Column(JSON)  # List of {day, hour, minute}
    
    # Temporary habits
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="habits")
    calendar_events = relationship("CalendarEvent", back_populates="habit", cascade="all, delete-orphan")

# --- Challenge System Models ---
from .models.challenges import Challenge, ChallengeParticipant, Quiz, Question, QuestionOption
