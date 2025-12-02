# app/routers/habits.py
from datetime import datetime, timedelta, time, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field

from app.models import Habit, CalendarEvent, User
from app.dependencies import get_current_user, get_db


router = APIRouter(
    prefix="/habits",
    tags=["Habits"],
)


# --- Pydantic Schemas ---
class TimeSlot(BaseModel):
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)


class WeeklyTimeSlot(BaseModel):
    day: int = Field(..., ge=0, le=6)  # 0=Sunday, 6=Saturday
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)


class MonthlyTimeSlot(BaseModel):
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)


class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_permanent: bool
    frequency: str = Field(..., pattern="^(daily|weekly|monthly)$")
    duration_minutes: int = Field(..., ge=1, le=600)  # 1 min to 10 hours
    
    # Daily
    repetitions_per_day: Optional[int] = None
    daily_times: Optional[List[TimeSlot]] = None
    
    # Weekly
    weekly_days: Optional[List[int]] = None  # [0-6]
    weekly_times: Optional[List[WeeklyTimeSlot]] = None
    
    # Monthly
    repetitions_per_month: Optional[int] = None
    monthly_days: Optional[List[int]] = None  # [1-31]
    monthly_times: Optional[List[MonthlyTimeSlot]] = None
    
    # Temporary
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class HabitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=600)
    is_active: Optional[bool] = None
    
    # Can update times
    daily_times: Optional[List[TimeSlot]] = None
    weekly_times: Optional[List[WeeklyTimeSlot]] = None
    monthly_times: Optional[List[MonthlyTimeSlot]] = None


class HabitResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_permanent: bool
    frequency: str
    duration_minutes: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# --- Helper Functions ---
def validate_habit_data(habit_data: HabitCreate):
    """Validate habit creation data based on frequency"""
    if habit_data.frequency == 'daily':
        if not habit_data.daily_times:
            raise ValueError("Daily habits require daily_times")
    elif habit_data.frequency == 'weekly':
        if not habit_data.weekly_times:
            raise ValueError("Weekly habits require weekly_times")
    elif habit_data.frequency == 'monthly':
        if not habit_data.monthly_times:
            raise ValueError("Monthly habits require monthly_times")
    
    if not habit_data.is_permanent:
        if not habit_data.start_date or not habit_data.end_date:
            raise ValueError("Temporary habits require start_date and end_date")
        if habit_data.end_date <= habit_data.start_date:
            raise ValueError("end_date must be after start_date")


def check_habit_conflicts(user_id: int, start_time: datetime, end_time: datetime, db: Session):
    """
    Check if there are conflicts with existing calendar events.
    Raises ValueError with conflict details if found.
    Short habits (1-10 min) are allowed to overlap.
    """
    # Calculate duration in minutes
    duration_minutes = (end_time - start_time).total_seconds() / 60
    
    # Short habits (1-10 min) can overlap with anything
    if 1 <= duration_minutes <= 10:
        return  # No conflict check needed
    
    # Check for overlapping events
    conflicts = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id,
        or_(
            and_(CalendarEvent.start_time <= start_time, CalendarEvent.end_time > start_time),
            and_(CalendarEvent.start_time < end_time, CalendarEvent.end_time >= end_time),
            and_(CalendarEvent.start_time >= start_time, CalendarEvent.end_time <= end_time)
        )
    ).all()
    
    # Filter out short-duration events (they can overlap)
    conflicts = [
        event for event in conflicts
        if (event.end_time - event.start_time).total_seconds() / 60 > 10
    ]
    
    if conflicts:
        conflict_details = []
        for event in conflicts:
            try:
                name = event.task.title if event.task else (event.habit.name if event.habit else "حدث غير معروف")
                start_str = event.start_time.strftime('%H:%M')
                end_str = event.end_time.strftime('%H:%M')
                conflict_details.append(f"{name} و من {start_str} الي {end_str}")
            except Exception as e:
                print(f"Error accessing event details: {e}")
                conflict_details.append("حدث (خطأ في التفاصيل)")
        
        raise ValueError(f"الوقت مستخدم من قبل في المهمه ({', '.join(conflict_details)})")


# --- CRUD Endpoints ---
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=HabitResponse)
def create_habit(
    habit_data: HabitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new habit"""
    try:
        # Check if habit with same name exists and is active
        existing_habit = db.query(Habit).filter(
            Habit.user_id == current_user.id,
            Habit.name == habit_data.name,
            Habit.is_active == True
        ).first()
        
        if existing_habit:
            raise HTTPException(status_code=400, detail="العاده مجدوله من قبل")

        validate_habit_data(habit_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in validation: {e}")
        raise HTTPException(status_code=500, detail="حدث خطا غير معروف")
    
    # Create habit
    try:
        habit = Habit(
            user_id=current_user.id,
            name=habit_data.name,
            description=habit_data.description,
            is_permanent=habit_data.is_permanent,
            frequency=habit_data.frequency,
            duration_minutes=habit_data.duration_minutes,
            repetitions_per_day=habit_data.repetitions_per_day,
            daily_times=[t.dict() for t in habit_data.daily_times] if habit_data.daily_times else None,
            weekly_days=habit_data.weekly_days,
            weekly_times=[t.dict() for t in habit_data.weekly_times] if habit_data.weekly_times else None,
            repetitions_per_month=habit_data.repetitions_per_month,
            monthly_days=habit_data.monthly_days,
            monthly_times=[t.dict() for t in habit_data.monthly_times] if habit_data.monthly_times else None,
            start_date=habit_data.start_date,
            end_date=habit_data.end_date,
        )
        
        db.add(habit)
        db.commit()
        db.refresh(habit)
        
        # Generate calendar events
        generate_habit_events(habit, db, current_user.id)
        
        return habit

    except ValueError as e:
        # Known error (conflict) during generation
        db.delete(habit)
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unknown error during creation/generation
        print(f"Error in creation/generation: {e}")
        import traceback
        traceback.print_exc()
        if 'habit' in locals():
            db.delete(habit)
            db.commit()
        raise HTTPException(status_code=500, detail="حدث خطا غير معروف")


@router.get("/", response_model=List[HabitResponse])
def get_habits(
    is_permanent: Optional[bool] = None,
    frequency: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all user habits"""
    query = db.query(Habit).filter(Habit.user_id == current_user.id)
    
    if is_permanent is not None:
        query = query.filter(Habit.is_permanent == is_permanent)
    if frequency:
        query = query.filter(Habit.frequency == frequency)
    if is_active is not None:
        query = query.filter(Habit.is_active == is_active)
    
    return query.order_by(Habit.created_at.desc()).all()


@router.get("/{habit_id}", response_model=HabitResponse)
def get_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get specific habit"""
    habit = db.query(Habit).filter(
        Habit.id == habit_id,
        Habit.user_id == current_user.id
    ).first()
    
    if not habit:
        raise HTTPException(status_code=404, detail="العادة غير موجودة")
    
    return habit


@router.delete("/{habit_id}", status_code=status.HTTP_200_OK)
def delete_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete habit and all its occurrences"""
    habit = db.query(Habit).filter(
        Habit.id == habit_id,
        Habit.user_id == current_user.id
    ).first()
    
    if not habit:
        raise HTTPException(status_code=404, detail="العادة غير موجودة")
    
    db.delete(habit)
    db.commit()
    
    return {"message": "تم حذف العادة بنجاح"}


@router.patch("/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: int,
    habit_data: HabitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update habit and regenerate all future calendar events.
    WARNING: This will delete all future events and create new ones with updated schedule.
    Custom times set from calendar will be lost.
    """
    habit = db.query(Habit).filter(
        Habit.id == habit_id,
        Habit.user_id == current_user.id
    ).first()
    
    if not habit:
        raise HTTPException(status_code=404, detail="العادة غير موجودة")
    
    # Update habit fields
    if habit_data.name is not None:
        habit.name = habit_data.name
    if habit_data.description is not None:
        habit.description = habit_data.description
    if habit_data.duration_minutes is not None:
        habit.duration_minutes = habit_data.duration_minutes
    if habit_data.is_active is not None:
        habit.is_active = habit_data.is_active
    
    # Update time slots
    if habit_data.daily_times is not None:
        habit.daily_times = [t.dict() for t in habit_data.daily_times]
    if habit_data.weekly_times is not None:
        habit.weekly_times = [t.dict() for t in habit_data.weekly_times]
    if habit_data.monthly_times is not None:
        habit.monthly_times = [t.dict() for t in habit_data.monthly_times]
    
    db.commit()
    db.refresh(habit)
    
    # Delete all FUTURE calendar events for this habit
    now = datetime.utcnow()
    deleted_count = db.query(CalendarEvent).filter(
        CalendarEvent.habit_id == habit_id,
        CalendarEvent.start_time >= now
    ).delete(synchronize_session=False)
    
    db.commit()
    
    print(f"Deleted {deleted_count} future events for habit {habit_id}")
    
    # Regenerate events with new schedule
    try:
        generate_habit_events(habit, db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"خطأ في إعادة الجدولة: {str(e)}")
    
    return habit


# --- Event Generation Logic ---
def generate_habit_events(habit: Habit, db: Session, user_id: int):
    """Generate calendar events for a habit"""
    if habit.frequency == 'daily':
        _generate_daily_events(habit, db, user_id)
    elif habit.frequency == 'weekly':
        _generate_weekly_events(habit, db, user_id)
    elif habit.frequency == 'monthly':
        _generate_monthly_events(habit, db, user_id)


def _generate_daily_events(habit: Habit, db: Session, user_id: int):
    """Generate events for daily habits"""
    if not habit.daily_times:
        return
    
    # Determine date range
    if habit.is_permanent:
        start = date.today()
        end = start + timedelta(days=90)  # Generate 3 months ahead
    else:
        start = habit.start_date
        end = habit.end_date
    
    current_date = start
    while current_date <= end:
        for time_slot in habit.daily_times:
            start_time = datetime.combine(current_date, time(time_slot['hour'], time_slot['minute']))
            end_time = start_time + timedelta(minutes=habit.duration_minutes)
            
            # Check conflicts
            try:
                check_habit_conflicts(user_id, start_time, end_time, db)
            except ValueError as e:
                raise ValueError(f"تعارض في {current_date}: {str(e)}")
            
            # Create event
            event = CalendarEvent(
                user_id=user_id,
                habit_id=habit.id,
                event_type='habit',
                start_time=start_time,
                end_time=end_time
            )
            db.add(event)
        
        current_date += timedelta(days=1)
    
    db.commit()


def _generate_weekly_events(habit: Habit, db: Session, user_id: int):
    """Generate events for weekly habits"""
    if not habit.weekly_times:
        return
    
    # Determine date range
    if habit.is_permanent:
        start = date.today()
        end = start + timedelta(days=365)  # Generate 1 year ahead for weekly habits
    else:
        start = habit.start_date
        end = habit.end_date
    
    current_date = start
    while current_date <= end:
        for time_slot in habit.weekly_times:
            if current_date.weekday() != (time_slot['day'] - 1) % 7:  # Adjust for Sunday=0
                continue
            
            start_time = datetime.combine(current_date, time(time_slot['hour'], time_slot['minute']))
            end_time = start_time + timedelta(minutes=habit.duration_minutes)
            
            try:
                check_habit_conflicts(user_id, start_time, end_time, db)
            except ValueError as e:
                raise ValueError(f"تعارض في {current_date}: {str(e)}")
            
            event = CalendarEvent(
                user_id=user_id,
                habit_id=habit.id,
                event_type='habit',
                start_time=start_time,
                end_time=end_time
            )
            db.add(event)
        
        current_date += timedelta(days=1)
    
    db.commit()


def _generate_monthly_events(habit: Habit, db: Session, user_id: int):
    """Generate events for monthly habits"""
    if not habit.monthly_times:
        return
    
    # Determine date range
    if habit.is_permanent:
        start = date.today()
        end = start + timedelta(days=1095)  # Generate 3 years ahead for monthly habits
    else:
        start = habit.start_date
        end = habit.end_date
    
    current_date = start
    while current_date <= end:
        for time_slot in habit.monthly_times:
            if current_date.day != time_slot['day']:
                continue
            
            start_time = datetime.combine(current_date, time(time_slot['hour'], time_slot['minute']))
            end_time = start_time + timedelta(minutes=habit.duration_minutes)
            
            try:
                check_habit_conflicts(user_id, start_time, end_time, db)
            except ValueError as e:
                raise ValueError(f"تعارض في {current_date}: {str(e)}")
            
            event = CalendarEvent(
                user_id=user_id,
                habit_id=habit.id,
                event_type='habit',
                start_time=start_time,
                end_time=end_time
            )
            db.add(event)
        
        current_date += timedelta(days=1)
    
    db.commit()
