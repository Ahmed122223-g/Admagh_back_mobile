
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
from . import models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def deactivate_expired_subscriptions():
    """
    Finds users with expired premium subscriptions and reverts them to the free plan.
    """
    db: Session = next(get_db())
    expired_users = db.query(models.User).filter(
        models.User.is_premium == True,
        models.User.expires_at != None,
        models.User.expires_at < datetime.utcnow()
    ).all()

    if not expired_users:
        print("INFO: No expired subscriptions to deactivate.")
        return

    for user in expired_users:
        print(f"INFO: Deactivating subscription for user {user.id}.")
        user.plan = "free"
        user.is_premium = False
        user.expires_at = None
        db.add(user)


    db.commit()
    print(f"INFO: Successfully deactivated {len(expired_users)} expired subscriptions.")


async def send_task_reminders():
    """
    Check for tasks starting in 30 minutes and mark for notifications.
    Called every 5 minutes by the scheduler.
    """
    from .routers.notifications import check_upcoming_tasks
    
    db: Session = next(get_db())
    try:
        notifications = await check_upcoming_tasks(db)
        if notifications:
            print(f"INFO: Sent {len(notifications)} task reminders.")
        else:
            print("INFO: No upcoming tasks to remind.")
    except Exception as e:
        print(f"ERROR: Failed to send task reminders: {e}")
    finally:
        db.close()
