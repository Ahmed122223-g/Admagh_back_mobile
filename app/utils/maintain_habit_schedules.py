"""
Background job to maintain rolling schedules for permanent habits.
Ensures permanent habits always have events scheduled for the appropriate future period.
"""
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from app.models import Habit, CalendarEvent
from app.database import SessionLocal


def get_schedule_period(frequency: str) -> int:
    """Get the number of days to schedule ahead based on frequency"""
    if frequency == 'daily':
        return 90  # 3 months
    elif frequency == 'weekly':
        return 365  # 1 year
    elif frequency == 'monthly':
        return 1095  # 3 years
    return 90


def maintain_habit_schedules():
    """Maintain rolling schedules for all permanent habits"""
    db = SessionLocal()
    try:
        # Get all active permanent habits
        permanent_habits = db.query(Habit).filter(
            Habit.is_permanent == True,
            Habit.is_active == True
        ).all()
        
        total_added = 0
        
        for habit in permanent_habits:
            added = _extend_habit_schedule(habit, db)
            total_added += added
        
        db.commit()
        print(f"✅ Schedule maintenance completed: {total_added} new events added across {len(permanent_habits)} habits")
        return total_added
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during schedule maintenance: {e}")
        raise
    finally:
        db.close()


def _extend_habit_schedule(habit: Habit, db: Session) -> int:
    """Extend schedule for a single habit if needed"""
    schedule_days = get_schedule_period(habit.frequency)
    target_end_date = date.today() + timedelta(days=schedule_days)
    
    # Get the last scheduled event for this habit
    last_event = db.query(CalendarEvent).filter(
        CalendarEvent.habit_id == habit.id
    ).order_by(CalendarEvent.start_time.desc()).first()
    
    if not last_event:
        # No events exist, generate from scratch
        print(f"  Habit {habit.id} ({habit.name}): No events found, skipping maintenance")
        return 0
    
    last_event_date = last_event.start_time.date()
    
    # If we still have enough future events, skip
    if last_event_date >= target_end_date:
        return 0
    
    # Generate missing events
    added_count = 0
    current_date = last_event_date + timedelta(days=1)
    
    while current_date <= target_end_date:
        if habit.frequency == 'daily':
            added_count += _add_daily_events(habit, current_date, db)
        elif habit.frequency == 'weekly':
            added_count += _add_weekly_events(habit, current_date, db)
        elif habit.frequency == 'monthly':
            added_count += _add_monthly_events(habit, current_date, db)
        
        current_date += timedelta(days=1)
    
    if added_count > 0:
        print(f"  Habit {habit.id} ({habit.name}): Added {added_count} new events")
    
    return added_count


def _add_daily_events(habit: Habit, current_date: date, db: Session) -> int:
    """Add daily events for a specific date"""
    if not habit.daily_times:
        return 0
    
    added = 0
    for time_slot in habit.daily_times:
        start_time = datetime.combine(current_date, time(time_slot['hour'], time_slot['minute']))
        end_time = start_time + timedelta(minutes=habit.duration_minutes)
        
        # Check if event already exists (avoid duplicates)
        existing = db.query(CalendarEvent).filter(
            CalendarEvent.habit_id == habit.id,
            CalendarEvent.start_time == start_time
        ).first()
        
        if not existing:
            event = CalendarEvent(
                user_id=habit.user_id,
                habit_id=habit.id,
                event_type='habit',
                start_time=start_time,
                end_time=end_time
            )
            db.add(event)
            added += 1
    
    return added


def _add_weekly_events(habit: Habit, current_date: date, db: Session) -> int:
    """Add weekly events for a specific date"""
    if not habit.weekly_times:
        return 0
    
    added = 0
    for time_slot in habit.weekly_times:
        # Check if current_date matches the day of week
        if current_date.weekday() != (time_slot['day'] - 1) % 7:
            continue
        
        start_time = datetime.combine(current_date, time(time_slot['hour'], time_slot['minute']))
        end_time = start_time + timedelta(minutes=habit.duration_minutes)
        
        existing = db.query(CalendarEvent).filter(
            CalendarEvent.habit_id == habit.id,
            CalendarEvent.start_time == start_time
        ).first()
        
        if not existing:
            event = CalendarEvent(
                user_id=habit.user_id,
                habit_id=habit.id,
                event_type='habit',
                start_time=start_time,
                end_time=end_time
            )
            db.add(event)
            added += 1
    
    return added


def _add_monthly_events(habit: Habit, current_date: date, db: Session) -> int:
    """Add monthly events for a specific date"""
    if not habit.monthly_times:
        return 0
    
    added = 0
    for time_slot in habit.monthly_times:
        # Check if current_date matches the day of month
        if current_date.day != time_slot['day']:
            continue
        
        start_time = datetime.combine(current_date, time(time_slot['hour'], time_slot['minute']))
        end_time = start_time + timedelta(minutes=habit.duration_minutes)
        
        existing = db.query(CalendarEvent).filter(
            CalendarEvent.habit_id == habit.id,
            CalendarEvent.start_time == start_time
        ).first()
        
        if not existing:
            event = CalendarEvent(
                user_id=habit.user_id,
                habit_id=habit.id,
                event_type='habit',
                start_time=start_time,
                end_time=end_time
            )
            db.add(event)
            added += 1
    
    return added


if __name__ == "__main__":
    # For manual testing
    maintain_habit_schedules()
