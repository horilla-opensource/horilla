import csv
from pathlib import Path
from collections import defaultdict

BANK_BRANCH_DATA = defaultdict(lambda: {"bank_code": "", "branches": {}})

csv_path = Path(__file__).resolve().parent / "bank_branch_list.csv"

with open(csv_path, newline='', encoding='cp1252') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        bank = row["bank_name"].strip()
        branch = row["branch_name"].strip()
        bank_code = row["bank_code"].strip()
        branch_code = row["branch_code"].strip()

        BANK_BRANCH_DATA[bank]["bank_code"] = bank_code
        BANK_BRANCH_DATA[bank]["branches"][branch] = branch_code

