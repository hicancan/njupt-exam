import pandas as pd

df = pd.read_excel("test_download.xlsx", engine='openpyxl')
b240402_raw = df[df.apply(lambda row: row.astype(str).str.contains('B240402').any(), axis=1)]
print(f"Found {len(b240402_raw)} exams for B240402 in the 17-18 week table!")
for idx, row in b240402_raw.iterrows():
    print(f"  - {row.get('课程名称', row.get('考试课程', 'Unknown'))}")
