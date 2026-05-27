import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "data/questions_with_answers.json"
TEXTS = [
    ROOT / "sources/text/blekitny-piotrus-materialy.txt",
    ROOT / "sources/text/szekla-materialy-czesc-1.txt",
    ROOT / "sources/text/wind-materialy.txt",
]
OUTPUT = ROOT / "data/answer_material_hits.json"

STOPWORDS = {
    "oraz",
    "jest",
    "przy",
    "jachtu",
    "jacht",
    "jachcie",
    "nalezy",
    "ktory",
    "ktora",
    "ktore",
    "mozna",
    "przez",
    "wody",
    "wodzie",
    "woda",
    "tak",
    "nie",
    "dla",
    "pod",
    "nad",
    "lub",
    "sie",
    "tym",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> set[str]:
    return {word for word in normalize(text).split() if len(word) > 3 and word not in STOPWORDS}


def main() -> None:
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    docs = {path.name: normalize(path.read_text(encoding="utf-8", errors="ignore")) for path in TEXTS}

    rows = []
    for question in questions:
        answer = normalize(question["correct_answer"])
        answer_tokens = tokens(question["correct_answer"])
        hits = {}
        for name, text in docs.items():
            exact = bool(answer and len(answer) >= 8 and answer in text)
            overlap = sorted(answer_tokens & set(text.split()))
            hits[name] = {
                "exact": exact,
                "keyword_overlap": len(overlap),
                "keywords": overlap[:12],
            }
        rows.append({"id": question["id"], "correct": question["correct"], "hits": hits})

    OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    exact_any = sum(any(hit["exact"] for hit in row["hits"].values()) for row in rows)
    keyword_any = sum(any(hit["keyword_overlap"] >= 2 for hit in row["hits"].values()) for row in rows)
    print(f"questions: {len(rows)}")
    print(f"exact_answer_phrase_in_materials: {exact_any}")
    print(f"two_or_more_answer_keywords_in_materials: {keyword_any}")
    print(f"output: {OUTPUT}")


if __name__ == "__main__":
    main()
