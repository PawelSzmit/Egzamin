import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "sources/ocr/pages"
OUTPUT = ROOT / "data/questions_official.json"

SPLIT_X = 1320


def clean(text: str) -> str:
    text = text.replace("|", " ")
    text = text.replace("_", " ")
    text = text.replace("/", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .:-")


def is_noise(text: str) -> bool:
    t = text.upper()
    return (
        not t
        or "POLSKI ZWIĄZEK" in t
        or "PONIATOWSK" in t
        or "WARSZAWA" in t
        or "REGON" in t
        or "NIP" in t
        or "NUMER ARKUSZA" in t
        or "STRONA" in t
        or "TEL." in t
        or "FAX" in t
        or "PYA.ORG" in t
        or "E-MAIL" in t
        or "EGZAMIN" in t
    )


def category_from(text: str) -> str | None:
    t = text.upper()
    if "BUDOWA JACHT" in t:
        return "Budowa jachtów"
    if "LOCJI" in t or "NAWIGACYJNE" in t:
        return "Podstawy locji i pomoce nawigacyjne"
    if "METEOROLOGIA" in t:
        return "Meteorologia"
    if "PRZEPISY" in t:
        return "Przepisy"
    if "RATOWNICTWO" in t:
        return "Ratownictwo"
    if "TEORIA ŻEGLOWANIA" in t or "TEORIA ZEGL" in t:
        return "Teoria żeglowania"
    return None


def page_lines(image: Path) -> list[dict]:
    out = subprocess.check_output(
        ["tesseract", str(image), "stdout", "-l", "pol", "--psm", "6", "tsv"],
        stderr=subprocess.DEVNULL,
        text=True,
    )
    rows = csv.DictReader(out.splitlines(), delimiter="\t")
    lines: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        word = row.get("text", "").strip()
        if not word:
            continue
        key = (row["block_num"], row["par_num"], row["line_num"])
        lines.setdefault(key, []).append(
            {
                "text": word,
                "left": int(row["left"]),
                "top": int(row["top"]),
                "right": int(row["left"]) + int(row["width"]),
                "bottom": int(row["top"]) + int(row["height"]),
            }
        )

    result = []
    for words in lines.values():
        words = sorted(words, key=lambda w: w["left"])
        left_words = [w["text"] for w in words if w["left"] < SPLIT_X]
        right_words = [w["text"] for w in words if w["left"] >= SPLIT_X]
        result.append(
            {
                "top": min(w["top"] for w in words),
                "left": min(w["left"] for w in words),
                "left_text": clean(" ".join(left_words)),
                "right_text": clean(" ".join(right_words)),
            }
        )
    return sorted(result, key=lambda x: (x["top"], x["left"]))


def parse_options(lines: list[str]) -> dict[str, str]:
    options: dict[str, list[str]] = {}
    current = None
    for raw in lines:
        text = clean(raw)
        if not text or is_noise(text):
            continue
        match = re.match(r"^(A|B|C|Cc|c|ą)\b\s*(.*)$", text)
        if match:
            marker = match.group(1)
            key = "C" if marker in {"Cc", "c"} else "A" if marker == "ą" else marker
            current = key
            options.setdefault(current, [])
            rest = clean(match.group(2))
            if rest:
                options[current].append(rest)
            continue
        if current:
            options[current].append(text)
    return {k: clean(" ".join(v)) for k, v in options.items()}


def parse() -> list[dict]:
    questions = []
    current_category = ""

    for page_index, image in enumerate(sorted(PAGES.glob("page-*.png")), start=1):
        lines = page_lines(image)
        page_questions = []

        for line in lines:
            for side in ("left_text", "right_text"):
                category = category_from(line[side])
                if category:
                    current_category = category

            text = line["left_text"]
            if is_noise(text) or category_from(text):
                continue
            if re.fullmatch(r"[A-Za-z]{1,5}", text) and not re.match(r"^\d+\.", text):
                continue

            match = re.match(r"^(\d+)\.\s*(.*)$", text)
            if match:
                page_questions.append(
                    {
                        "id": int(match.group(1)),
                        "category": current_category,
                        "page": page_index,
                        "top": line["top"],
                        "question_parts": [match.group(2)],
                        "options": {},
                    }
                )
                continue

            if page_questions and text:
                page_questions[-1]["question_parts"].append(text)

        for idx, question in enumerate(page_questions):
            next_top = page_questions[idx + 1]["top"] if idx + 1 < len(page_questions) else 10_000
            option_lines = [
                line["right_text"]
                for line in lines
                if question["top"] - 12 <= line["top"] < next_top - 8 and line["right_text"]
            ]
            question["options"] = parse_options(option_lines)
            question["question"] = clean(" ".join(question.pop("question_parts")))
            question.pop("top")
            questions.append(question)

    return questions


def main() -> None:
    questions = parse()
    OUTPUT.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = [q["id"] for q in questions if set(q["options"]) != {"A", "B", "C"}]
    duplicate_ids = sorted({q["id"] for q in questions if [x["id"] for x in questions].count(q["id"]) > 1})
    print(f"questions: {len(questions)}")
    print(f"first_id: {questions[0]['id'] if questions else '-'} last_id: {questions[-1]['id'] if questions else '-'}")
    print(f"missing_options: {missing}")
    print(f"duplicate_ids: {duplicate_ids}")
    print(f"output: {OUTPUT}")


if __name__ == "__main__":
    main()
