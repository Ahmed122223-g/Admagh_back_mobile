# app/models/habit.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Time, Date, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Type
    is_permanent = Column(Boolean, nullable=False, default=True, index=True)
    frequency = Column(String(20), nullable=False, index=True)  # 'daily', 'weekly', 'monthly'
    
    # Duration
    duration_minutes = Column(Integer, nullable=False, default=30)
    
    # Daily habits
    repetitions_per_day = Column(Integer)  # For daily: how many times
    daily_times = Column(JSON)  # List of {hour, minute}
    
    # Weekly habits
    weekly_days = Column(JSON)  # List of day names or numbers
    weekly_times = Column(JSON)  # List of {day, hour, minute}
    
    # Monthly habits
    repetitions_per_month = Column(Integer)  # For monthly: how many times
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
