import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "eval", "reports")


def main() -> None:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    reports = sorted(name for name in os.listdir(REPORTS_DIR) if name.endswith(".json"))
    print(json.dumps({"reports": reports[-5:]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
