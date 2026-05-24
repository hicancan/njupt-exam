import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QRELS_PATH = os.path.join(BASE_DIR, "eval", "qrels.json")


def main() -> None:
    with open(QRELS_PATH, "r", encoding="utf-8") as handle:
        qrels = json.load(handle)
    print(json.dumps({"qrels": len(qrels), "path": QRELS_PATH}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
