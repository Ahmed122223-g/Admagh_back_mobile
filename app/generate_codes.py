import os
import sys
import uuid

# Add the project root to the python path to allow imports from the app module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


ACTIVATION_CODES_FILE = os.path.join(os.path.dirname(__file__), "activation_codes.txt")

def generate_random_code(prefix: str) -> str:
    """Generates a random, unique code with a given prefix."""
    random_part = str(uuid.uuid4()).replace("-", "")[:12].upper()
    return f"{prefix}-{random_part}"

def get_existing_codes_from_file() -> set:
    """Reads the activation codes file and returns a set of existing codes."""
    if not os.path.exists(ACTIVATION_CODES_FILE):
        return set()
    with open(ACTIVATION_CODES_FILE, "r", encoding="utf-8") as f:
        # Reads "CODE,TYPE" and returns just the code part
        return {line.strip().split(",")[0] for line in f if line.strip() and not line.startswith("#")}


def create_codes_for_file(plan_type: str, prefix: str, quantity: int):
    """Creates a specified quantity of unique codes for a given plan type, ensuring they are not in the file."""
    existing_codes = get_existing_codes_from_file()
    new_codes = []
    for _ in range(quantity):
        code_str = generate_random_code(prefix)
        while code_str in existing_codes:
            code_str = generate_random_code(prefix)
        new_codes.append(f"{code_str},{plan_type}")
        existing_codes.add(code_str) # Add to set to prevent duplicates in the same run
    return new_codes

def main():
    """Main function to generate and save activation codes."""
    # This main function is now primarily for testing the file-based generation
    # or for manual database population if needed. The manage_codes.py script
    # should be the primary interface for code generation.

    print("Generating codes and saving to activation_codes.txt...")

    try:
        all_new_codes = []
        print(f"\n--- Generating 10 Weekly Codes (WKL) ---")
        weekly_codes = create_codes_for_file("weekly", "WKL", 10)
        all_new_codes.extend(weekly_codes)
        for code in weekly_codes:
            print(code)

        print(f"\n--- Generating 100 Monthly Codes (MTH) ---")
        monthly_codes = create_codes_for_file("monthly", "MTH", 100)
        all_new_codes.extend(monthly_codes)
        for code in monthly_codes:
            print(code)

        print(f"\n--- Generating 100 Yearly Codes (YRL) ---")
        yearly_codes = create_codes_for_file("yearly", "YRL", 100)
        all_new_codes.extend(yearly_codes)
        for code in yearly_codes:
            print(code)

        print(f"\n--- Generating 100 Lifetime Codes (LTM) ---")
        lifetime_codes = create_codes_for_file("lifetime", "LTM", 100)
        all_new_codes.extend(lifetime_codes)
        for code in lifetime_codes:
            print(code)

        with open(ACTIVATION_CODES_FILE, "a", encoding="utf-8") as f:
            for code_line in all_new_codes:
                f.write(f"{code_line}\n")

        print(
            f"\nSuccessfully generated and saved {len(all_new_codes)} new activation codes to {ACTIVATION_CODES_FILE}!"
        )

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
