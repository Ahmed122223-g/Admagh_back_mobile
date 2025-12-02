from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..database import get_db
from ..dependencies import ActiveUser

router = APIRouter(
    prefix="/friends",
    tags=["الأصدقاء (Friends)"],
)

@router.post("/request", response_model=schemas.FriendshipRead)
def send_friend_request(
    friendship: schemas.FriendshipCreate,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    if current_user.id == friendship.friend_id:
        raise HTTPException(status_code=400, detail="لا يمكنك إرسال طلب صداقة لنفسك")

    # Check if friend_id exists
    friend_user = crud.get_user_by_id(db, friendship.friend_id)
    if not friend_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    # Check for existing request or friendship
    existing_friendship = db.query(models.Friendship).filter(
        ((models.Friendship.user_id == current_user.id) & (models.Friendship.friend_id == friendship.friend_id)) |
        ((models.Friendship.user_id == friendship.friend_id) & (models.Friendship.friend_id == current_user.id))
    ).first()

    if existing_friendship:
        if existing_friendship.status == "pending":
            if existing_friendship.user_id == current_user.id:
                raise HTTPException(status_code=400, detail="REQUEST_ALREADY_SENT")
            else:
                raise HTTPException(status_code=400, detail="USER_SENT_REQUEST_ERROR")
        elif existing_friendship.status == "accepted":
            raise HTTPException(status_code=400, detail="USER_IS_FRIEND_ERROR")

    try:
        db_friendship = crud.send_friend_request(db, current_user.id, friendship.friend_id)
        if not db_friendship:
            raise HTTPException(status_code=500, detail="فشل إرسال طلب الصداقة")
        return db_friendship
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في قاعدة البيانات: {e}")

@router.post("/accept/{friendship_id}", response_model=schemas.FriendshipRead)
def accept_friend_request(
    friendship_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    friendship = crud.get_friendship(db, friendship_id)
    if not friendship:
        raise HTTPException(status_code=404, detail="طلب الصداقة غير موجود")
    if friendship.friend_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك إذن لقبول طلب الصداقة هذا")
    if friendship.status != "pending":
        raise HTTPException(status_code=400, detail="لا يمكن قبول طلب صداقة غير معلق")
    
    return crud.accept_friend_request(db, friendship)

@router.post("/reject/{friendship_id}", response_model=schemas.FriendshipRead)
def reject_friend_request(
    friendship_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    friendship = crud.get_friendship(db, friendship_id)
    if not friendship:
        raise HTTPException(status_code=404, detail="طلب الصداقة غير موجود")
    if friendship.friend_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك إذن لرفض طلب الصداقة هذا")
    if friendship.status != "pending":
        raise HTTPException(status_code=400, detail="لا يمكن رفض طلب صداقة غير معلق")
    
    return crud.reject_friend_request(db, friendship)

@router.get("/", response_model=List[schemas.Friend])
def get_friends_list(
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    friends = crud.get_friends_list(db, current_user.id)
    return [schemas.Friend(id=f.id, name=f.name, email=f.email) for f in friends]

@router.get("/requests", response_model=List[schemas.FriendRequest])
def get_incoming_friend_requests(
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    requests = crud.get_incoming_friend_requests(db, current_user.id)
    return [
        schemas.FriendRequest(
            id=req.id,
            sender_id=req.user_id,
            sender_name=crud.get_user_by_id(db, req.user_id).name,
            created_at=req.created_at,
        )
        for req in requests
    ]


@router.get("/sent-requests", response_model=List[schemas.FriendRequest])
def get_sent_friend_requests(
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """Get all friend requests sent by current user (pending)"""
    requests = crud.get_sent_friend_requests(db, current_user.id)
    return [
        schemas.FriendRequest(
            id=req.id,
            sender_id=current_user.id,
            sender_name=crud.get_user_by_id(db, req.friend_id).name,  # Recipient's name
            created_at=req.created_at,
        )
        for req in requests
    ]


@router.get("/search/{user_id_or_email}", response_model=schemas.UserSearchRead)
def search_user(
    user_id_or_email: str,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    try:
        user_id = int(user_id_or_email)
        found_user = crud.get_user_by_id(db, user_id)
    except ValueError:
        found_user = crud.get_user_by_email(db, user_id_or_email)

    if not found_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if found_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك البحث عن نفسك")

    # Check friendship status
    friendship = db.query(models.Friendship).filter(
        ((models.Friendship.user_id == current_user.id) & (models.Friendship.friend_id == found_user.id)) |
        ((models.Friendship.user_id == found_user.id) & (models.Friendship.friend_id == current_user.id))
    ).first()

    status = "none"
    if friendship:
        if friendship.status == "accepted":
            status = "friends"
        elif friendship.status == "pending":
            if friendship.user_id == current_user.id:
                status = "pending_sent"
            else:
                status = "pending_received"

    return schemas.UserSearchRead(
        id=found_user.id, 
        name=found_user.name, 
        email=found_user.email,
        friendship_status=status
    )

@router.post("/cancel/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_friend_request(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """Cancel a sent friend request"""
    # Find the pending request sent by current user
    friendship = db.query(models.Friendship).filter(
        models.Friendship.user_id == current_user.id,
        models.Friendship.friend_id == friend_id,
        models.Friendship.status == "pending"
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="لا يوجد طلب صداقة معلق لهذا المستخدم")
        
    db.delete(friendship)
    db.commit()
    return None

@router.get("/{friend_id}/profile")
def get_friend_profile(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """Get detailed friend profile with statistics"""
    # Check if they are friends (unless viewing own profile)
    if friend_id != current_user.id:
        friendship = db.query(models.Friendship).filter(
            ((models.Friendship.user_id == current_user.id) & (models.Friendship.friend_id == friend_id)) |
            ((models.Friendship.user_id == friend_id) & (models.Friendship.friend_id == current_user.id)),
            models.Friendship.status == "accepted"
        ).first()
        
        if not friendship:
            raise HTTPException(status_code=403, detail="يمكنك فقط عرض ملفات تعريف أصدقائك")
    
    # Get friend user
    friend = crud.get_user_by_id(db, friend_id)
    if not friend:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # Get task statistics
    total_tasks = db.query(models.Task).filter(models.Task.owner_id == friend_id).count()
    completed_tasks = db.query(models.Task).filter(
        models.Task.owner_id == friend_id,
        models.Task.completed == True
    ).count()
    
    return {
        "id": friend.id,
        "name": friend.name,
        "email": friend.email,
        "created_at": friend.created_at,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks
    }



@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    if not crud.remove_friendship(db, current_user.id, friend_id):
        raise HTTPException(status_code=404, detail="الصداقة غير موجودة")