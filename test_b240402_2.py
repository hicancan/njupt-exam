import pandas as pd
import glob
import os

for file in glob.glob("public/data/*.xlsx"):
    print(f"Checking {os.path.basename(file)}...")
    try:
        df = pd.read_excel(file, engine='openpyxl')
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
        else:
            print(f"  No B240402 rows found.")
    except Exception as e:
        print(f"  Failed to read: {e}")
