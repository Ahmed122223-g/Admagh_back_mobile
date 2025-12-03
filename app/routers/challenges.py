from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ..database import get_db
from ..models import User
from ..models.challenges import Challenge, ChallengeParticipant, Quiz, Question, QuestionOption
from ..schemas.challenges import (
    ChallengeCreate, ChallengeResponse, ChallengeListResponse, ChallengeSubmission
)
from ..dependencies import get_current_user # Assuming this exists

router = APIRouter(
    prefix="/challenges",
    tags=["challenges"],
)

@router.post("/", response_model=ChallengeResponse)
def create_challenge(
    challenge_data: ChallengeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validation
    if challenge_data.is_quiz and not challenge_data.quiz_data:
        raise HTTPException(status_code=400, detail="Quiz data required for quiz challenge")

    # 2. Create Challenge
    expires_at = datetime.utcnow() + timedelta(hours=challenge_data.lifespan_hours)
    
    db_challenge = Challenge(
        creator_id=current_user.id,
        name=challenge_data.name,
        description=challenge_data.description,
        duration_minutes=challenge_data.duration_minutes,
        is_quiz=challenge_data.is_quiz,
        lifespan_hours=challenge_data.lifespan_hours,
        expires_at=expires_at
    )
    db.add(db_challenge)
    db.flush() # Get ID

    # 3. Create Quiz if needed
    if challenge_data.is_quiz and challenge_data.quiz_data:
        db_quiz = Quiz(
            challenge_id=db_challenge.id,
            duration_minutes=challenge_data.quiz_data.duration_minutes
        )
        db.add(db_quiz)
        db.flush()

        for q in challenge_data.quiz_data.questions:
            db_question = Question(
                quiz_id=db_quiz.id,
                text=q.text,
                type=q.type,
                explanation=q.explanation
            )
            db.add(db_question)
            db.flush()
            
            for opt in q.options:
                db_option = QuestionOption(
                    question_id=db_question.id,
                    text=opt.text,
                    is_correct=opt.is_correct
                )
                db.add(db_option)

    # 4. Add Participants
    # Invite friends
    for friend_id in challenge_data.invited_friend_ids:
        # Verify friend exists (optional but good)
        participant = ChallengeParticipant(
            challenge_id=db_challenge.id,
            user_id=friend_id,
            status="invited"
        )
        db.add(participant)

    # If NOT quiz, creator is also a participant
    if not challenge_data.is_quiz:
        creator_participant = ChallengeParticipant(
            challenge_id=db_challenge.id,
            user_id=current_user.id,
            status="accepted" # Auto-accept
        )
        db.add(creator_participant)

    db.commit()
    db.refresh(db_challenge)
    return db_challenge

@router.get("/", response_model=List[ChallengeListResponse])
def get_challenges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get challenges where user is creator OR participant
    # Note: If quiz, creator might not be participant, but we should still show it?
    # "List of challenges" usually implies ones I'm participating in or created.
    
    # Subquery for participation
    participant_subquery = db.query(ChallengeParticipant.challenge_id).filter(
        ChallengeParticipant.user_id == current_user.id
    ).subquery()

    challenges = db.query(Challenge).filter(
        or_(
            Challenge.creator_id == current_user.id,
            Challenge.id.in_(participant_subquery)
        )
    ).all()

    # Map to response
    results = []
    for c in challenges:
        # Determine status
        my_participant = next((p for p in c.participants if p.user_id == current_user.id), None)
        my_status = my_participant.status if my_participant else "creator"
        
        status_str = "active"
        if datetime.utcnow() > c.expires_at:
            status_str = "expired"
        
        results.append(ChallengeListResponse(
            id=c.id,
            name=c.name,
            status=status_str,
            is_quiz=c.is_quiz,
            created_at=c.created_at,
            expires_at=c.expires_at,
            my_status=my_status
        ))
    
    return results

@router.get("/{challenge_id}", response_model=ChallengeResponse)
def get_challenge_details(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    # Check access (creator or participant)
    is_participant = any(p.user_id == current_user.id for p in challenge.participants)
    if challenge.creator_id != current_user.id and not is_participant:
        raise HTTPException(status_code=403, detail="Not authorized")

    return challenge

@router.post("/{challenge_id}/respond")
def respond_to_invite(
    challenge_id: int,
    accept: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    if participant.status != "invited":
        raise HTTPException(status_code=400, detail="Already responded")

    participant.status = "accepted" if accept else "rejected"
    db.commit()
    return {"status": participant.status}

@router.post("/{challenge_id}/start")
def start_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.user_id == current_user.id
    ).first()
    
    if not participant or participant.status != "accepted":
        raise HTTPException(status_code=400, detail="Cannot start challenge")

    if participant.start_time:
        raise HTTPException(status_code=400, detail="Already started")

    participant.start_time = datetime.utcnow()
    db.commit()
    return {"start_time": participant.start_time}

@router.post("/{challenge_id}/finish")
def finish_challenge(
    challenge_id: int,
    submission: ChallengeSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    participant = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.user_id == current_user.id
    ).first()
    
    if not participant or not participant.start_time:
        raise HTTPException(status_code=400, detail="Challenge not started")
        
    if participant.end_time:
        raise HTTPException(status_code=400, detail="Already finished")

    participant.end_time = datetime.utcnow()
    
    # Calculate time taken
    diff = participant.end_time - participant.start_time
    participant.time_taken_seconds = int(diff.total_seconds())
    participant.status = "completed"

    # Calculate Score if Quiz
    if challenge.is_quiz and challenge.quiz:
        score = 0
        total_questions = len(challenge.quiz.questions)
        
        # Create a map of correct answers
        correct_map = {} # question_id -> correct_option_id
        for q in challenge.quiz.questions:
            for opt in q.options:
                if opt.is_correct:
                    correct_map[q.id] = opt.id
        
        correct_count = 0
        for ans in submission.answers:
            if ans.question_id in correct_map and correct_map[ans.question_id] == ans.selected_option_id:
                correct_count += 1
        
        if total_questions > 0:
            participant.score = (correct_count / total_questions) * 100
        else:
            participant.score = 0

    db.commit()
    return {"status": "completed", "score": participant.score, "time_taken": participant.time_taken_seconds}
