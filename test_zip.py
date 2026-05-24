import zipfile
filename = "public/data/2025-2026学年第二学期考试安排表（学校组织17-18周）-学生用表.xlsx"
try:
    with zipfile.ZipFile(filename) as zf:
        print("Zip file is valid. Contents:")
        print(zf.namelist()[:5])
except Exception as e:
    print(f"Error reading zip: {e}")
