from datetime import datetime
from sqlalchemy.orm import Session
from ..models import User
from ..models.challenges import Challenge, ChallengeParticipant
from ..database import SessionLocal

def process_expired_challenges():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find expired challenges
        expired_challenges = db.query(Challenge).filter(Challenge.expires_at <= now).all()
        
        for challenge in expired_challenges:
            # Check if all ACCEPTED participants have finished
            # If someone accepted but hasn't started/finished, we might need to wait or force finish?
            # Requirement: "results saved until everyone finishes"
            # But also "after lifespan ends... delete".
            # Let's assume "everyone finishes" means everyone who STARTED.
            # If they haven't started by expiration, they missed out.
            
            participants = challenge.participants
            all_finished = True
            active_participants = []
            
            for p in participants:
                if p.status == "accepted":
                    if p.start_time and not p.end_time:
                        # Still running?
                        # Check if their personal timer ran out?
                        # If so, force finish.
                        time_elapsed = (now - p.start_time).total_seconds()
                        max_duration = challenge.duration_minutes * 60
                        if challenge.is_quiz and challenge.quiz:
                             max_duration += (challenge.quiz.duration_minutes * 60)
                        
                        if time_elapsed > (max_duration + 300): # 5 min buffer
                             # Force finish
                             p.end_time = now
                             p.time_taken_seconds = int(time_elapsed)
                             p.status = "completed"
                             # Score remains 0 or whatever
                        else:
                            all_finished = False
                    elif not p.start_time:
                        # Accepted but never started.
                        # Since challenge expired, they can't start now.
                        # Treat as "did not participate" or "0 score"?
                        # Let's ignore them for ranking.
                        pass
                
                if p.status == "completed":
                    active_participants.append(p)

            if not all_finished:
                continue # Skip this challenge for now, wait for runners to finish

            # Calculate Winners
            # Sort by Score (Desc) then Time (Asc)
            # For non-quiz, Score is None, so just Time (Asc)
            
            if challenge.is_quiz:
                sorted_participants = sorted(
                    active_participants, 
                    key=lambda p: (-1 * (p.score or 0), p.time_taken_seconds or 999999)
                )
            else:
                sorted_participants = sorted(
                    active_participants, 
                    key=lambda p: (p.time_taken_seconds or 999999)
                )

            # Award Cups
            if sorted_participants:
                # Gold
                winner = sorted_participants[0]
                user = db.query(User).filter(User.id == winner.user_id).first()
                if user:
                    user.gold_cups += 1
                
                if len(sorted_participants) >= 10:
                    if len(sorted_participants) > 1:
                        # Silver
                        silver = sorted_participants[1]
                        u2 = db.query(User).filter(User.id == silver.user_id).first()
                        if u2: u2.silver_cups += 1
                    
                    if len(sorted_participants) > 2:
                        # Bronze
                        bronze = sorted_participants[2]
                        u3 = db.query(User).filter(User.id == bronze.user_id).first()
                        if u3: u3.bronze_cups += 1

            # Increment count for all completed
            for p in active_participants:
                u = db.query(User).filter(User.id == p.user_id).first()
                if u:
                    u.challenges_count += 1

            # Delete Challenge (Cascade deletes Quiz, Participants, Questions)
            db.delete(challenge)
            db.commit()
            
    except Exception as e:
        print(f"Error in process_expired_challenges: {e}")
        db.rollback()
    finally:
        db.close()
