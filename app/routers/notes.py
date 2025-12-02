# app/routers/notes.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..dependencies import ActiveUser

router = APIRouter(
    prefix="/notes",
    tags=["الملاحظات (Notes)"],
    responses={404: {"description": "الملاحظة غير موجودة"}},
)


@router.post("/", response_model=schemas.NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(
    note: schemas.NoteCreate,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """إنشاء ملاحظة جديدة للمستخدم الحالي"""
    return crud.create_user_note(db=db, note=note, user_id=current_user.id)


@router.get("/", response_model=List[schemas.NoteRead])
def read_notes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """جلب جميع ملاحظات المستخدم الحالي"""
    notes = crud.get_notes(db, user_id=current_user.id, skip=skip, limit=limit)
    return notes


@router.put("/{note_id}", response_model=schemas.NoteRead)
def update_note_route(
    note_id: int,
    note: schemas.NoteUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """تعديل ملاحظة معينة للمستخدم الحالي"""
    db_note = crud.update_note(
        db, note_id=note_id, user_id=current_user.id, note_in=note
    )
    if db_note is None:
        raise HTTPException(status_code=404, detail="الملاحظة غير موجودة")
    return db_note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_route(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(ActiveUser),
):
    """حذف ملاحظة معينة للمستخدم الحالي"""
    if not crud.delete_note(db, note_id=note_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="الملاحظة غير موجودة")
    return
