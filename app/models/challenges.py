from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger, Float
)
from sqlalchemy.orm import relationship
from ..database import Base

class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False)  # Duration of the challenge itself
    is_quiz = Column(Boolean, default=False)
    lifespan_hours = Column(Integer, default=24)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False) # calculated based on lifespan

    creator = relationship("User", backref="created_challenges")
    participants = relationship("ChallengeParticipant", back_populates="challenge", cascade="all, delete-orphan")
    quiz = relationship("Quiz", uselist=False, back_populates="challenge", cascade="all, delete-orphan")

class ChallengeParticipant(Base):
    __tablename__ = "challenge_participants"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="invited")
    
    # Results
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True) 
    
    challenge = relationship("Challenge", back_populates="participants")
    user = relationship("User")

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False, unique=True)
    duration_minutes = Column(Integer, nullable=False) 

    challenge = relationship("Challenge", back_populates="quiz")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    text = Column(Text, nullable=False)
    type = Column(String, nullable=False) # 'mcq', 'true_false'
    explanation = Column(Text, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")

class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("Question", back_populates="options")
