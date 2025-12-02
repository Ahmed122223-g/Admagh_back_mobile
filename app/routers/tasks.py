# app/routers/tasks.py
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import (TaskBase, TaskCreate, TaskRead, TaskTimerAction, TaskUpdate)

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)

@router.get(
    "/active/", response_model=Optional[TaskRead], status_code=status.HTTP_200_OK
)
def get_active_task_endpoint(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    GET /tasks/active
    جلب المهمة النشطة حالياً. يعيد null إذا لم يتم العثور على مهمة نشطة.
    """
    active_task = crud.get_active_task(db, user_id=current_user.id)
    return active_task  # Returns None if no active task


@router.post("/{task_id}/start_timer", response_model=TaskRead)
def start_task_timer_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /tasks/{id}/start_timer (يحل خطأ 404)
    بدء المؤقت أو استئنافه.
    """
    task = crud.start_task_timer(db, task_id=task_id, user_id=current_user.id)
    if task is None:
        raise HTTPException(
            status_code=404, detail="Task not found or unable to start."
        )
    if isinstance(task, dict) and "error" in task:
        raise HTTPException(
            status_code=400, detail=task["error"]
        )  # لخطأ "مهمة أخرى نشطة"
    return task


@router.post("/{task_id}/stop_timer", response_model=TaskRead)
def stop_task_timer_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /tasks/{id}/stop_timer (يحل خطأ 404)
    إيقاف المؤقت وحفظ التقدم (يستخدم للإيقاف المؤقت).
    """
    task = crud.stop_task_timer(db, task_id=task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(
            status_code=404, detail="Active task not found or already stopped."
        )
    return task


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete_task_endpoint(
    task_id: int,
    action: TaskTimerAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /tasks/{id}/complete (يحل خطأ 404)
    وسم المهمة كمكتملة وحفظ تقدمها.
    """
    task = crud.complete_task(
        db,
        task_id=task_id,
        user_id=current_user.id,
        progress_details=action.progress_details,
    )
    if not task:
        raise HTTPException(
            status_code=404, detail="Task not found or unable to complete."
        )
    return task


@router.post("/{task_id}/mark_incomplete", response_model=TaskRead)
def mark_task_incomplete_endpoint(
    task_id: int,
    action: TaskTimerAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    وسم المهمة كغير مكتملة (يضيف ساعة إضافية للمرة القادمة).
    """
    task = crud.mark_task_incomplete(
        db,
        task_id=task_id,
        user_id=current_user.id,
        progress_details=action.progress_details,
    )
    if not task:
        raise HTTPException(
            status_code=404, detail="Task not found or unable to mark incomplete."
        )
    return task


@router.post("/", response_model=TaskRead)
def create_task_for_user(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # يجب أن تكون هذه الدالة موجودة في crud.py
    return crud.create_user_task(db=db, task=task, user_id=current_user.id)


@router.get("/", response_model=List[TaskRead])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = crud.get_tasks(db, user_id=current_user.id, skip=skip, limit=limit)
    return tasks


@router.put("/{task_id}", response_model=TaskRead)
def update_task_data(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_task = crud.update_task(
        db, task_id=task_id, task_in=task_in, user_id=current_user.id
    )
    if updated_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if updated_task == "completed":
        raise HTTPException(status_code=400, detail="Completed tasks cannot be edited.")
    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_data(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = crud.delete_task(db, task_id=task_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}
