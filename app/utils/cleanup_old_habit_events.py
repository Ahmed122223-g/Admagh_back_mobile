"""
Background job to cleanup old habit calendar events.
Runs daily to remove events that have passed.
"""
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.models import CalendarEvent
from app.database import SessionLocal


def cleanup_old_habit_events():
    """Delete calendar events for habits that are in the past"""
    db = SessionLocal()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Delete habit events before today
        deleted_count = db.query(CalendarEvent).filter(
            CalendarEvent.event_type == 'habit',
            CalendarEvent.start_time < today
        ).delete(synchronize_session=False)
        
        db.commit()
        
        print(f"✅ Cleanup completed: {deleted_count} old habit events deleted")
        return deleted_count
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during cleanup: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # For manual testing
    cleanup_old_habit_events()
