import json
import pandas as pd
import glob
import os

with open("public/data/all_exams.json", "r", encoding="utf-8") as f:
    data = json.load(f)

b240402_parsed = [item for item in data if "B240402" in str(item.get("class_name", ""))]
print(f"Parsed exams for B240402: {len(b240402_parsed)}")
for exam in b240402_parsed:
    print(f"  - {exam['course_name']} ({exam.get('date', 'no-date')} {exam.get('raw_time', '')})")

print("\n--- Searching raw excel files ---")
for file in glob.glob("public/data/*.xlsx"):
    print(f"Checking {os.path.basename(file)}...")
    df = pd.read_excel(file)
    # Check all columns for B240402
    b240402_raw = df[df.apply(lambda row: row.astype(str).str.contains('B240402').any(), axis=1)]
    if not b240402_raw.empty:
        print(f"Found {len(b240402_raw)} rows in {os.path.basename(file)}")
        for idx, row in b240402_raw.iterrows():
            print(f"Row {idx+2}:")
            for col in df.columns:
                val = row[col]
                if pd.notna(val) and val != "":
                    print(f"    {col}: {val}")
