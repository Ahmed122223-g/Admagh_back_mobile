# app/routers/calendar.py
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app import crud, schemas
from app.dependencies import get_current_user, get_db
from app.models import User, CalendarEvent, Task

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"],
)


def validate_schedule_time(
    user_id: int,
    start_time: datetime,
    end_time: datetime,
    db: Session,
    exclude_event_id: Optional[int] = None
):
    """
    Validate that start_time is in future and no overlapping events exist.
    Events with 1-10 minute duration are allowed to overlap.
    """
    # Check if start_time is in future
    if start_time < datetime.utcnow():
        raise ValueError("لا يمكن جدولة مهمة في الماضي")
    
    # Calculate duration in minutes
    duration_minutes = (end_time - start_time).total_seconds() / 60
    
    # Short tasks (1-10 min) can overlap with anything
    if 1 <= duration_minutes <= 10:
        return  # No conflict check needed for short tasks
    
    # Build query for overlapping events
    query = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id,
        or_(
            # New event starts during existing event
            and_(CalendarEvent.start_time <= start_time, CalendarEvent.end_time > start_time),
            # New event ends during existing event
            and_(CalendarEvent.start_time < end_time, CalendarEvent.end_time >= end_time),
            # New event completely contains existing event
            and_(CalendarEvent.start_time >= start_time, CalendarEvent.end_time <= end_time)
        )
    )
    
    # Exclude current event if updating
    if exclude_event_id:
        query = query.filter(CalendarEvent.id != exclude_event_id)
    
    conflicts = query.all()
    
    # Filter out short-duration events (they can overlap)
    conflicts = [
        event for event in conflicts
        if (event.end_time - event.start_time).total_seconds() / 60 > 10
    ]
    
    if conflicts:
        conflict_details = []
        for event in conflicts:
            name = event.task.title if event.task else (event.habit.name if event.habit else "حدث غير معروف")
            start_str = event.start_time.strftime('%H:%M')
            end_str = event.end_time.strftime('%H:%M')
            conflict_details.append(f"{name} من {start_str} الي {end_str}")
            
        raise ValueError(f"الوقت مستخدم من قبل في المهمه ({', '.join(conflict_details)})")


@router.post("/schedule/{task_id}", status_code=status.HTTP_201_CREATED)
def schedule_task(
    task_id: int,
    start_time: datetime,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Schedule a task on the calendar.
    """
    try:
        # Get task
        task = crud.get_task(db, task_id=task_id, user_id=current_user.id)
        if not task or task.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="المهمة غير موجودة")
        
        # Check if task is already scheduled
        existing_event = db.query(CalendarEvent).filter(
            CalendarEvent.task_id == task_id
        ).first()
        
        if existing_event:
            raise HTTPException(status_code=400, detail="المهمه مجدوله من قبل")
        
        # Calculate end_time based on estimated_hours
        duration_hours = task.estimated_hours or 1.0
        end_time = start_time + timedelta(hours=duration_hours)
        
        # Validate schedule time
        validate_schedule_time(current_user.id, start_time, end_time, db)
        
        # Create calendar event
        calendar_event = CalendarEvent(
            user_id=current_user.id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time
        )
        
        db.add(calendar_event)
        db.commit()
        db.refresh(calendar_event)
        
        return {
            "id": calendar_event.id,
            "task_id": task_id,
            "task_title": task.title,
            "start_time": start_time,
            "end_time": end_time,
            "message": "تم جدولة المهمة بنجاح"
        }
    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unknown error in schedule_task: {e}")
        raise HTTPException(status_code=500, detail="حدث خطا غير معروف")


@router.delete("/unschedule/{event_id}")
def unschedule_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a scheduled event.
    - For task events: Removes the task from calendar
    - For habit events: Removes ONLY this specific occurrence (not the habit itself)
    """
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id,
        CalendarEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="الحدث غير موجود")
    
    # Delete the single event (habit itself remains intact if event_type='habit')
    db.delete(event)
    db.commit()
    
    if event.event_type == 'habit':
        return {"message": "تم حذف الجدولة لهذا اليوم فقط"}
    else:
        return {"message": "تم حذف الجدولة بنجاح"}


@router.delete("/events/{event_id}")
def delete_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a calendar event (alias for unschedule_event for frontend compatibility).
    """
    return unschedule_event(event_id, db, current_user)


@router.patch("/events/{event_id}")
def update_calendar_event(
    event_id: int,
    start_time: datetime,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the time for a single calendar event.
    Works for both task and habit events.
    For habits: only affects THIS occurrence (not the entire habit schedule).
    """
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id,
        CalendarEvent.user_id == current_user.id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="الحدث غير موجود")
    
    # Calculate duration based on event type
    if event.event_type == 'habit' and event.habit:
        duration_minutes = event.habit.duration_minutes
    elif event.event_type == 'task' and event.task:
        duration_minutes = (event.task.estimated_hours or 1.0) * 60
    else:
        # Fallback: keep existing duration
        duration_minutes = (event.end_time - event.start_time).total_seconds() / 60
    
    # Calculate new end_time
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    # Validate new time (check conflicts, except for short events)
    try:
        validate_schedule_time(
            current_user.id,
            start_time,
            end_time,
            db,
            exclude_event_id=event_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Update event times
    event.start_time = start_time
    event.end_time = end_time
    
    db.commit()
    db.refresh(event)
    
    if event.event_type == 'habit':
        return {
            "message": "تم تحديث ميعاد هذا اليوم فقط",
            "id": event.id,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat()
        }
    else:
        return {
            "message": "تم تحديث الميعاد بنجاح",
            "id": event.id,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat()
        }
def check_availability(
    start_time: datetime,
    duration_hours: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if a time slot is available.
    Returns conflicts if any.
    """
    end_time = start_time + timedelta(hours=duration_hours)
    
    # Check for overlapping events
    conflicts = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id,
        or_(
            and_(CalendarEvent.start_time <= start_time, CalendarEvent.end_time > start_time),
            and_(CalendarEvent.start_time < end_time, CalendarEvent.end_time >= end_time),
            and_(CalendarEvent.start_time >= start_time, CalendarEvent.end_time <= end_time)
        )
    ).all()
    
    if conflicts:
        return {
            "available": False,
            "conflicts": [
                {
                    "task_title": event.task.title if event.task else (event.habit.name if event.habit else "حدث غير معروف"),
                    "start_time": event.start_time,
                    "end_time": event.end_time
                }
                for event in conflicts
            ]
        }
    
    return {"available": True, "conflicts": []}


@router.get("/upcoming")
def get_upcoming_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get upcoming events (next 7 days).
    """
    now = datetime.utcnow()
    end_date = now + timedelta(days=7)
    
    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time >= now,
        CalendarEvent.start_time <= end_date
    ).order_by(CalendarEvent.start_time).all()
    
    return [
        {
            "id": event.id,
            "task_id": event.task_id,
            "task_title": event.task.title if event.task else (event.habit.name if event.habit else "حدث غير معروف"),
            "start_time": event.start_time,
            "end_time": event.end_time
        }
        for event in events
    ]


@router.get("/events")
def get_calendar_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all calendar events for the current user within a date range.
    Returns both task events and habit events.
    """
    query = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id
    )
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(CalendarEvent.start_time >= start_date)
    if end_date:
        query = query.filter(CalendarEvent.end_time <= end_date)
    
    # Order by start time
    events = query.order_by(CalendarEvent.start_time).all()
    
    # Format response
    result = []
    for event in events:
        event_data = {
            "id": event.id,
            "event_type": event.event_type,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "created_at": event.created_at.isoformat(),
        }
        
        # Add task or habit specific data
        if event.event_type == 'task' and event.task:
            event_data.update({
                "task_id": event.task_id,
                "title": event.task.title,
                "description": event.task.description,
                "priority": event.task.priority,
                "status": event.task.status,
            })
        elif event.event_type == 'habit' and event.habit:
            event_data.update({
                "habit_id": event.habit_id,
                "title": event.habit.name,
                "description": event.habit.description,
                "frequency": event.habit.frequency,
                "is_permanent": event.habit.is_permanent,
            })
        
        result.append(event_data)
    
    return result


@router.get("/scheduled-tasks")
def get_scheduled_task_ids(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all task IDs that are scheduled.
    Only returns task events, not habit events.
    """
    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.event_type == 'task',  # Only get task events
        CalendarEvent.task_id.isnot(None)     # Ensure task_id is not null
    ).all()
    
    return {"scheduled_task_ids": [event.task_id for event in events]}
