import glob
for f in glob.glob("public/data/*.xlsx"):
    with open(f, "rb") as file:
        header = file.read(8)
        print(f"{f}: {header}")
