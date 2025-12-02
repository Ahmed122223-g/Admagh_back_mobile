# app/routers/notifications.py
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CalendarEvent

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


async def check_upcoming_tasks(db: Session):
    """
    Check for tasks starting in 30 minutes and send notifications.
    This should be called by a background scheduler every 5 minutes.
    """
    now = datetime.utcnow()
    target_time_start = now + timedelta(minutes=25)  # 25 minutes from now
    target_time_end = now + timedelta(minutes=35)  # 35 minutes from now
    
    # Get events starting in 30 minutes (±5 minute window)
    upcoming_events = db.query(CalendarEvent).filter(
        CalendarEvent.start_time >= target_time_start,
        CalendarEvent.start_time <= target_time_end,
        CalendarEvent.notification_sent == False
    ).all()
    
    notifications = []
    for event in upcoming_events:
        # Send notification (this would integrate with FCM or your notification service)
        notification_data = {
            "user_id": event.user_id,
            "task_id": event.task_id,
            "task_title": event.task.title,
            "start_time": event.start_time,
            "message": f"مهمة قادمة: {event.task.title} بعد 30 دقيقة"
        }
        
        notifications.append(notification_data)
        
        # Mark notification as sent
        event.notification_sent = True
    
    db.commit()
    
    return notifications


@router.get("/upcoming-reminders")
async def get_upcoming_reminders(db: Session = Depends(get_db)):
    """
    Manual endpoint to check and send upcoming task reminders.
    In production, this would be called by a background scheduler.
    """
    notifications = await check_upcoming_tasks(db)
    return {
        "count": len(notifications),
        "notifications": notifications
    }
