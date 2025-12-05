import argparse
import os
import sys
from collections import defaultdict

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generate_codes import create_codes_for_file, ACTIVATION_CODES_FILE

def list_unused_codes():
    """Lists all unused codes from the file, grouped by plan type."""
    print(f"--- Listing All Unused Activation Codes from {ACTIVATION_CODES_FILE} ---")
    if not os.path.exists(ACTIVATION_CODES_FILE):
        print("Activation codes file not found.")
        return

    with open(ACTIVATION_CODES_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not lines:
        print("No unused codes found.")
        return

    codes_by_plan = defaultdict(list)
    for line in lines:
        try:
            code, plan_type = line.split(",")
            codes_by_plan[plan_type].append(code)
        except ValueError:
            print(f"Skipping malformed line: {line}")

    for plan_type, codes in sorted(codes_by_plan.items()):
        print(f"\n--- {plan_type.capitalize()} Codes ---")
        for code in codes:
            print(code)


def add_new_codes(plan_type: str, quantity: int):
    """Generates and adds new codes to the activation file."""
    if plan_type not in ["weekly", "monthly", "yearly", "lifetime"]:
        print(
            f"Error: Invalid plan type '{plan_type}'. Must be one of: weekly, monthly, yearly, lifetime."
        )
        return

    prefix_map = {"weekly": "WKL", "monthly": "MTH", "yearly": "YRL", "lifetime": "LTM"}
    prefix = prefix_map[plan_type]

    print(f"Generating {quantity} new {plan_type} code(s)...")
    new_codes = create_codes_for_file(plan_type, prefix, quantity)

    with open(ACTIVATION_CODES_FILE, "a", encoding="utf-8") as f:
        for code_line in new_codes:
            f.write(f"{code_line}\n")

    print("\n--- Generated New Codes ---")
    for code_line in new_codes:
        print(code_line)
    print(f"\nSuccessfully created and saved {quantity} new {plan_type} code(s) to {ACTIVATION_CODES_FILE}.")

def delete_code(code_str: str):
    """Deletes a specific code from the activation file."""
    if not os.path.exists(ACTIVATION_CODES_FILE):
        print(f"Error: Activation codes file not found.")
        return

    with open(ACTIVATION_CODES_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    code_found = False
    updated_lines = []
    for line in lines:
        # Keep comments and lines that don't match the code to be deleted
        if line.startswith("#") or not line.startswith(f"{code_str},"):
            updated_lines.append(line)
        else:
            code_found = True

    if not code_found:
        print(f"Error: Code '{code_str}' not found in the file.")
        return

    with open(ACTIVATION_CODES_FILE, "w", encoding="utf-8") as f:
        for line in updated_lines:
            f.write(f"{line}\n")

    print(f"Successfully deleted code '{code_str}' from {ACTIVATION_CODES_FILE}.")

def main():
    parser = argparse.ArgumentParser(
        description=f"Manage activation codes in {ACTIVATION_CODES_FILE}."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # 'list' command
    parser_list = subparsers.add_parser(
        "list", help="List all unused activation codes from the file."
    )

    # 'add' command
    parser_add = subparsers.add_parser("add", help="Add new activation codes to the file.")
    parser_add.add_argument(
        "--plan",
        type=str,
        required=True,
        choices=["weekly", "monthly", "yearly", "lifetime"],
        help="The subscription plan type.",
    )
    parser_add.add_argument(
        "--quantity", type=int, required=True, help="The number of codes to generate."
    )

    # 'delete' command
    parser_delete = subparsers.add_parser(
        "delete", help="Delete a code from the activation file."
    )
    parser_delete.add_argument(
        "code", type=str, help="The exact code string to delete."
    )

    args = parser.parse_args()

    if args.command == "list":
        list_unused_codes()
    elif args.command == "add":
        add_new_codes(args.plan, args.quantity)
    elif args.command == "delete":
        delete_code(args.code)

if __name__ == "__main__":
    main()
