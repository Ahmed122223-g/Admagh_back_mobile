from .pusher import pusher_client

import asyncio

# app/crud.py
from datetime import datetime, timedelta, date
from typing import List, Optional, Any
import os
import threading
import secrets
import random
from firebase_admin import messaging

from pydantic import BaseModel
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from . import models, schemas, utils
from .auth_utils import get_password_hash, verify_password

ACTIVATION_CODES_FILE = os.path.join(
    os.path.dirname(__file__), "activation_codes.txt"
)

file_lock = threading.Lock()

def create_password_reset_token(db: Session, user: models.User) -> str:
    token = secrets.token_urlsafe(32)
    user.reset_password_token = token
    user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.add(user)
    db.commit()
    db.refresh(user)
    return token


def get_user_by_password_reset_token(db: Session, token: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.reset_password_token == token).first()


def update_password(db: Session, user: models.User, new_password: str):
    user.hashed_password = get_password_hash(new_password)
    user.reset_password_token = None
    user.reset_password_token_expires = None
    db.add(user)
    db.commit()
    db.refresh(user)


def generate_password_reset_code(db: Session, email: str) -> Optional[str]:
    user = get_user_by_email(db, email)
    if not user:
        return None

    code = ''.join(random.choices('0123456789', k=6))
    user.reset_password_code = code
    user.reset_password_code_expires = datetime.utcnow() + timedelta(minutes=10) 
    db.add(user)
    db.commit()
    db.refresh(user)
    return code

def verify_password_reset_code(db: Session, email: str, code: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None

    if user.reset_password_code == code and \
       user.reset_password_code_expires and \
       user.reset_password_code_expires > datetime.utcnow():
        return user
    return None

def reset_user_password(db: Session, user: models.User, new_password: str):
    user.hashed_password = get_password_hash(new_password)
    user.reset_password_code = None
    user.reset_password_code_expires = None
    db.add(user)
    db.commit()
    db.refresh(user)


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_firebase_uid(db: Session, firebase_uid: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()

def get_user_by_verification_token(db: Session, token: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.verification_token == token).first()

def set_user_verified(db: Session, user: models.User) -> models.User:
    user.is_verified = True
    user.verification_token = None # Clear the token after verification
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_fcm_token(db: Session, user_id: int, fcm_token: str) -> Optional[models.User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    db_user.fcm_token = fcm_token
    db.commit()
    db.refresh(db_user)
    return db_user

def get_or_create_user_by_firebase_uid(db: Session, firebase_uid: str, email: str, name: str) -> models.User:
    user = get_user_by_firebase_uid(db, firebase_uid)
    if user:
        # If user exists but is not verified, verify them automatically (Firebase/Google accounts are trusted)
        if not user.is_verified:
            user.is_verified = True
            db.commit()
            db.refresh(user)
        return user
    
    # If user doesn't exist by firebase_uid, check by email
    user = get_user_by_email(db, email)
    if user:
        # Link existing user to Firebase UID and verify them
        user.firebase_uid = firebase_uid
        if not user.is_verified:
            user.is_verified = True  # Auto-verify Google sign-in users
        db.commit()
        db.refresh(user)
        return user

    # If no user found, create a new one with is_verified=True for Google accounts
    new_user_id = utils.generate_unique_id(db)
    db_user = models.User(
        id=new_user_id,
        firebase_uid=firebase_uid,
        email=email,
        name=name,
        hashed_password=get_password_hash(secrets.token_urlsafe(16)), # Generate a random password for Firebase users
        is_active=True,
        is_verified=True,  # Auto-verify Google/Firebase authenticated users
        is_unlocked=False,
        plan="free",
        is_premium=False,
        premium_plan=None,
        reset_password_token=None,
        reset_password_token_expires=None,
        reset_password_code=None,
        reset_password_code_expires=None,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return get_user_by_id(db, user_id)


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    print("Inside create_user function")
    hashed_password = get_password_hash(user.password)
    print(f"Password hashed for user: {user.email}")

    new_user_id = utils.generate_unique_id(db)
    print(f"Generated unique ID: {new_user_id}")

    verification_token = secrets.token_urlsafe(32)

    db_user = models.User(
        id=new_user_id,
        email=user.email,
        name=user.name,
        hashed_password=hashed_password,
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
        is_unlocked=False,
        plan="free",
        subscription_id=None,
        expires_at=None,
        is_premium=False,
        premium_plan=user.premium_plan,
        reset_password_token=None,
        reset_password_token_expires=None,
        reset_password_code=None,
        reset_password_code_expires=None,
    )
    print("User model instance created")

    try:
        print("Adding user to session")
        db.add(db_user)
        print("Committing to database")
        db.commit()
        print("Commit successful")
        db.refresh(db_user)
        print("User refreshed from database")
        return db_user
    except Exception as e:
        print(f"!!! EXCEPTION DURING DB COMMIT IN create_user: {e}")
        print(f"!!! User ID that caused the error: {new_user_id}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e


def set_user_unlocked(
    db: Session, user_id: int, unlocked: bool = True
) -> Optional[models.User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    db_user.is_unlocked = unlocked
    db.commit()
    db.refresh(db_user)
    return db_user


def update_subscription(
    db: Session, user_id: int, subscription: schemas.SubscriptionUpdate
) -> Optional[models.User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    update_data = subscription.model_dump(exclude_unset=True)
    if "plan" in update_data:
        db_user.plan = update_data["plan"]
    if "is_premium" in update_data:
        db_user.is_premium = update_data["is_premium"]
    if "subscription_id" in update_data:
        db_user.subscription_id = update_data["subscription_id"]
    if "expires_at" in update_data:
        db_user.expires_at = update_data["expires_at"]

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False

    db.query(models.Task).filter(models.Task.owner_id == user_id).delete()
    db.query(models.Note).filter(models.Note.owner_id == user_id).delete()

    db.query(models.ActivationCode).filter(
        models.ActivationCode.used_by_user_id == user_id
    ).update(
        {
            models.ActivationCode.used_by_user_id: None,
            models.ActivationCode.is_used: False,
            models.ActivationCode.used_at: None,
        }
    )

    db.delete(db_user)
    db.commit()
    return True


def use_activation_code(db: Session, code: str, user_id: int) -> Optional[str]:
    """
    Checks for an activation code in the database, and if found and unused, marks it as used.
    Returns the plan type on success, or an error string on failure.
    """
    db_code = db.query(models.ActivationCode).filter(models.ActivationCode.code == code).first()

    if not db_code:
        return "not_found"

    if db_code.is_used:
        return "already_used"

    db_code.is_used = True
    db_code.used_by_user_id = user_id
    db_code.used_at = datetime.utcnow()
    db.commit()
    db.refresh(db_code)
    return db_code.plan_type

def update_user_subscription(
    db: Session, user: models.User, plan_type: str
) -> models.User:
    """Updates a user's subscription based on the plan type."""
    user.is_premium = True
    user.premium_plan = plan_type

    if plan_type == "monthly":
        user.subscription_expiry_date = datetime.utcnow() + timedelta(days=30)
    elif plan_type == "yearly":
        user.subscription_expiry_date = datetime.utcnow() + timedelta(days=365)
    elif plan_type == "lifetime":
        user.subscription_expiry_date = None
    else:
        user.is_premium = False
        user.subscription_expiry_date = None

    db.commit()
    db.refresh(user)
    return user


def update_item(db: Session, db_item: Any, item_in: BaseModel):
    update_data = item_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(db_item, key):
            setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item

def get_active_task(db: Session, user_id: int) -> Optional[models.Task]:
    today = datetime.utcnow().date()
    return (
        db.query(models.Task)
        .filter(
            models.Task.owner_id == user_id,
            models.Task.completed == False,
            func.date(models.Task.due_date) == today,
        )
        .first()
    )


def start_task_timer(db: Session, task_id: int, user_id: int):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user_id).first()
    if not task:
        return None

    active_task = get_active_task(db, user_id)
    if active_task and active_task.id != task_id:
        return {"error": "Another task is already running."}

    if task.status == "COMPLETED":
        return {"error": "لا يمكن بدء مهمة مكتملة."}
        
    if task.status == "INCOMPLETE":
        new_remaining_time = 3600 
    elif task.status == "TO_DO" or task.remaining_time_seconds <= 0:
        new_remaining_time = task.initial_duration_seconds
    else:
        new_remaining_time = task.remaining_time_seconds

    task.is_active = True
    task.start_time = datetime.utcnow()
    task.status = "IN_PROGRESS"
    task.remaining_time_seconds = new_remaining_time
    task.last_run_date = datetime.utcnow()

    db.commit()
    db.refresh(task)
    return task

def stop_task_timer(db: Session, task_id: int, user_id: int):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user_id).first()
    if not task or not task.is_active:
        return None

    elapsed_time = (datetime.utcnow() - task.start_time).total_seconds()
    task.time_spent_seconds += int(elapsed_time)
    task.remaining_time_seconds = max(
        0, task.remaining_time_seconds - int(elapsed_time)
    )

    task.is_active = False
    task.start_time = None

    db.commit()
    db.refresh(task)
    return task

def complete_task(
    db: Session, task_id: int, user_id: int, progress_details: str = None
):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user_id).first()
    if not task:
        return None

    task.status = "COMPLETED"
    task.completed = True
    if progress_details is not None:
        task.progress_details = progress_details
    db.commit()
    db.refresh(task)
    return task

def mark_task_incomplete(
    db: Session, task_id: int, user_id: int, progress_details: str = None
):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.owner_id == user_id).first()
    if not task:
        return None

    task.status = "INCOMPLETE"
    task.completed = False
    if progress_details is not None:
        task.progress_details = progress_details
    db.commit()
    db.refresh(task)
    return task

def end_of_day_cleanup(db: Session):
    tasks_to_mark_incomplete = (
        db.query(models.Task)
        .filter(
            models.Task.status.in_(["TO_DO", "IN_PROGRESS"]),
            models.Task.is_active == False,
        )
        .all()
    )

    for task in tasks_to_mark_incomplete:
        if task.is_active:
            stop_task_timer(db, task.id, task.owner_id)

        task.status = "INCOMPLETE"
        db.add(task)

    db.commit()
    return {
        "message": f"تم نقل {len(tasks_to_mark_incomplete)} مهمة إلى المهام غير المكتملة."
    }

def get_tasks(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[models.Task]:
    tasks = (
        db.query(models.Task)
        .filter(models.Task.owner_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    print(f"Found {len(tasks)} tasks for user {user_id}")
    for task in tasks:
        print(f"Task ID: {task.id}, Owner ID: {task.owner_id}")
    return tasks

def get_task(db: Session, task_id: int, user_id: int) -> Optional[models.Task]:
    return (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.owner_id == user_id)
        .first()
    )

def create_user_task(
    db: Session, task: schemas.TaskCreate, user_id: int
) -> models.Task:
    initial_duration_seconds = int(task.estimated_hours * 3600)
    task_data = task.model_dump(exclude={'google_event_id'})
    db_task = models.Task(
        **task_data,
        owner_id=user_id,
        initial_duration_seconds=initial_duration_seconds,
        remaining_time_seconds=initial_duration_seconds,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(
    db: Session, task_id: int, user_id: int, task_in: schemas.TaskUpdate
) -> Optional[models.Task]:
    db_task = get_task(db, task_id, user_id)
    if db_task:
        if db_task.completed:
            return "completed" 
        
        # Update the task
        updated_task = update_item(db, db_task, task_in)
        
        # Update associated calendar event if exists
        calendar_event = db.query(models.CalendarEvent).filter(
            models.CalendarEvent.task_id == task_id
        ).first()
        
        if calendar_event:
            should_update = False
            new_start_time = calendar_event.start_time
            new_duration = calendar_event.end_time - calendar_event.start_time
            
            if task_in.due_date is not None:
                new_start_time = task_in.due_date
                should_update = True
                
            if task_in.estimated_hours is not None:
                new_duration = timedelta(hours=task_in.estimated_hours)
                should_update = True
                
            if should_update:
                calendar_event.start_time = new_start_time
                calendar_event.end_time = new_start_time + new_duration
                db.add(calendar_event)
                db.commit()
                db.refresh(calendar_event)
                
        return updated_task
    return None

def delete_task(db: Session, task_id: int, user_id: int) -> bool:
    db_task = get_task(db, task_id, user_id)
    if db_task:
        db.delete(db_task)
        db.commit()
        return True
    return False

def get_notes(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[models.Note]:
    return (
        db.query(models.Note)
        .filter(models.Note.owner_id == user_id)
        .order_by(models.Note.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def create_user_note(
    db: Session, note: schemas.NoteCreate, user_id: int
) -> models.Note:
    db_note = models.Note(**note.model_dump(), owner_id=user_id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def update_note(
    db: Session, note_id: int, user_id: int, note_in: schemas.NoteUpdate
) -> Optional[models.Note]:
    db_note = (
        db.query(models.Note)
        .filter(models.Note.id == note_id, models.Note.owner_id == user_id)
        .first()
    )
    return update_item(db, db_note, note_in) if db_note else None

def delete_note(db: Session, note_id: int, user_id: int) -> bool:

    db_note = (

        db.query(models.Note)

        .filter(models.Note.id == note_id, models.Note.owner_id == user_id)

        .first()

    )

    if db_note:
        db.delete(db_note)
        db.commit()
        return True

    return False


def send_friend_request(db: Session, user_id: int, friend_id: int) -> Optional[models.Friendship]:
    # Check if a request already exists in either direction or if they are already friends
    existing_request = db.query(models.Friendship).filter(
        ((models.Friendship.user_id == user_id) & (models.Friendship.friend_id == friend_id)) |
        ((models.Friendship.user_id == friend_id) & (models.Friendship.friend_id == user_id))
    ).first()

    if existing_request:
        return None # Request already exists or they are already friends

    db_friendship = models.Friendship(user_id=user_id, friend_id=friend_id, status="pending")
    db.add(db_friendship)
    db.commit()
    db.refresh(db_friendship)
    
    try:
        sender = get_user_by_id(db, user_id)
        friend = get_user_by_id(db, friend_id)
        if friend and friend.fcm_token and sender:
            message = messaging.Message(
                token=friend.fcm_token,
                data={
                    'type': 'friend_request',
                    'title': 'Friend Request',
                    'body': f'{sender.name} sent you a friend request!',
                    'sender_id': str(user_id),
                    'sender_name': sender.name,
                },
            )
            messaging.send(message)
            print(f"Sent FCM friend request notification to user {friend_id}")
    except Exception as e:
        print(f"Error sending FCM notification for friend request: {e}")

    return db_friendship

def get_friendship(db: Session, friendship_id: int) -> Optional[models.Friendship]:
    return db.query(models.Friendship).filter(models.Friendship.id == friendship_id).first()

def accept_friend_request(db: Session, friendship: models.Friendship) -> models.Friendship:
    friendship.status = "accepted"
    db.commit()
    db.refresh(friendship)
    return friendship

def reject_friend_request(db: Session, friendship: models.Friendship) -> models.Friendship:
    friendship.status = "rejected"
    db.commit()
    db.refresh(friendship)
    return friendship

def get_friends_list(db: Session, user_id: int) -> List[models.User]:
    # Get accepted friendships where current user is user_id
    friends_as_user = db.query(models.User).join(models.Friendship, models.User.id == models.Friendship.friend_id).filter(
        (models.Friendship.user_id == user_id) & (models.Friendship.status == "accepted")
    ).all()
    
    # Get accepted friendships where current user is friend_id
    friends_as_friend = db.query(models.User).join(models.Friendship, models.User.id == models.Friendship.user_id).filter(
        (models.Friendship.friend_id == user_id) & (models.Friendship.status == "accepted")
    ).all()
    
    return list(set(friends_as_user + friends_as_friend))  # Use set to remove duplicates


def get_incoming_friend_requests(db: Session, user_id: int) -> List[models.Friendship]:
    return db.query(models.Friendship).filter(
        (models.Friendship.friend_id == user_id) & (models.Friendship.status == "pending")
    ).all()


def get_sent_friend_requests(db: Session, user_id: int) -> List[models.Friendship]:
    """Get all friend requests sent by the user (still pending)"""
    return db.query(models.Friendship).filter(
        (models.Friendship.user_id == user_id) & (models.Friendship.status == "pending")
    ).all()


def find_user_by_id_or_email(db: Session, identifier: Any) -> Optional[models.User]:
    if isinstance(identifier, int):
        return db.query(models.User).filter(models.User.id == identifier).first()
    elif isinstance(identifier, str):
        return db.query(models.User).filter(models.User.email == identifier).first()
    return None


def remove_friendship(db: Session, user_id: int, friend_id: int) -> bool:
    # Find the friendship in either direction
    friendship = db.query(models.Friendship).filter(
        ((models.Friendship.user_id == user_id) & (models.Friendship.friend_id == friend_id) & (models.Friendship.status == "accepted")) |
        ((models.Friendship.user_id == friend_id) & (models.Friendship.friend_id == user_id) & (models.Friendship.status == "accepted"))
    ).first()

    if friendship:
        db.delete(friendship)
        db.commit()
        return True
    return False



