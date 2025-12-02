import os
import sys
from sqlalchemy.orm import Session

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, engine
from app.models import ActivationCode

ACTIVATION_CODES_FILE = os.path.join(
    os.path.dirname(__file__), "activation_codes.txt"
)

def import_codes_from_file():
    """Imports activation codes from the text file into the database."""
    db: Session = SessionLocal()
    print(f"--- Importing Codes from {ACTIVATION_CODES_FILE} ---")

    if not os.path.exists(ACTIVATION_CODES_FILE):
        print("Activation codes file not found.")
        return

    with open(ACTIVATION_CODES_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not lines:
        print("No codes to import.")
        return

    imported_count = 0
    for line in lines:
        try:
            code_str, plan_type = line.split(",")
            code_str = code_str.strip()
            plan_type = plan_type.strip()

            # Check if the code already exists
            existing_code = db.query(ActivationCode).filter(ActivationCode.code == code_str).first()
            if existing_code:
                continue

            # Add the new code
            db_code = ActivationCode(
                code=code_str,
                plan_type=plan_type,
                is_used=False,
            )
            db.add(db_code)
            imported_count += 1

        except ValueError:
            print(f"Skipping malformed line: {line}")

    db.commit()
    db.close()
    print(f"Successfully imported {imported_count} new codes.")

if __name__ == "__main__":
    import_codes_from_file()
