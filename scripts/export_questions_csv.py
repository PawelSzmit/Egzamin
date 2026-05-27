import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/questions_with_answers.json"
OUTPUT = ROOT / "data/questions_with_answers.csv"


def main() -> None:
    rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "category",
                "question",
                "answer_a",
                "answer_b",
                "answer_c",
                "correct",
                "correct_answer",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row["id"],
                    "category": row["category"],
                    "question": row["question"],
                    "answer_a": row["options"]["A"],
                    "answer_b": row["options"]["B"],
                    "answer_c": row["options"]["C"],
                    "correct": row["correct"],
                    "correct_answer": row["correct_answer"],
                }
            )
    print(f"output: {OUTPUT}")


if __name__ == "__main__":
    main()
