# App utilities
import random
from sqlalchemy.orm import Session

def generate_unique_id(db: Session) -> int:
    """Generate a unique 15-digit ID for a user."""
    from .. import models  # Import inside function to avoid circular imports
    while True:
        new_id = random.randint(100000000000000, 999999999999999)
        if not db.query(models.User).filter(models.User.id == new_id).first():
            return new_id
