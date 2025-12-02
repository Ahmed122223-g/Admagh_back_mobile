import random
from sqlalchemy.orm import Session
from .models import User

def generate_unique_id(db: Session) -> int:
    """Generates a unique 9-digit random ID for a new user."""
    while True:
        # Generate a random 9-digit number (between 100,000,000 and 999,999,999)
        new_id = random.randint(100_000_000, 999_999_999)
        # Check if the ID already exists in the database
        if not db.query(User).filter(User.id == new_id).first():
            return new_id