import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/text/pytania-egzaminacyjne-zj-ocr.txt"
OUTPUT = ROOT / "data/questions_raw.json"

CATEGORIES = {
    "BUDOWA JACHTÓW",
    "PODSTAWY LOCJI I POMOCE NAWIGACYJNE",
    "METEOROLOGIA",
    "PRZEPISY",
    "RATOWNICTWO",
    "TEORIA ŻEGLOWANIA",
}


def clean_line(line: str) -> str:
    line = line.replace("\f", "").strip()
    line = re.sub(r"\s+", " ", line)
    return line


def is_noise(line: str) -> bool:
    if not line:
        return True
    noise_bits = [
        "POLSKI ZWIĄZEK ŻEGLARSKI",
        "Poniatowskiego",
        "Warszawa",
        "REGON",
        "Numer arkusza:",
        "Strona ",
        "tel.",
        "fax",
        "mail:",
        "pya.org",
    ]
    return any(bit in line for bit in noise_bits)


def detect_category(line: str) -> str | None:
    upper = line.upper()
    for category in CATEGORIES:
        if category in upper:
            return category.title()
    return None


def split_options(text: str) -> tuple[str, dict[str, str]]:
    text = re.sub(r"\s+", " ", text).strip()
    marker = re.compile(r"(?<![A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż])([ABC])\s*(?:[|/_]+)?\s+")
    matches = list(marker.finditer(text))
    if len(matches) < 3:
        return text, {}

    # Keep the first A/B/C sequence in order. OCR sometimes reads random letters as markers.
    best = None
    for i, m in enumerate(matches):
        seq = [m]
        wanted = {"A": "B", "B": "C"}
        for n in matches[i + 1 :]:
            if seq[-1].group(1) in wanted and n.group(1) == wanted[seq[-1].group(1)]:
                seq.append(n)
                if len(seq) == 3:
                    best = seq
                    break
        if best:
            break
    if not best:
        return text, {}

    q = text[: best[0].start()].strip(" :-")
    options: dict[str, str] = {}
    for idx, m in enumerate(best):
        key = m.group(1)
        end = best[idx + 1].start() if idx + 1 < len(best) else len(text)
        options[key] = text[m.end() : end].strip(" |")
    return q, options


def parse() -> list[dict]:
    rows = []
    current_category = ""
    current = None

    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = clean_line(raw)
        if is_noise(line):
            continue
        category = detect_category(line)
        if category:
            current_category = category
            continue

        match = re.match(r"^(\d+)\.\s*(.*)$", line)
        if match:
            if current:
                rows.append(current)
            current = {
                "id": int(match.group(1)),
                "category": current_category,
                "raw": match.group(2).strip(),
            }
            continue

        if current:
            current["raw"] += " " + line

    if current:
        rows.append(current)

    parsed = []
    for row in rows:
        question, options = split_options(row["raw"])
        parsed.append(
            {
                "id": row["id"],
                "category": row["category"],
                "question": question,
                "options": options,
                "raw": row["raw"],
            }
        )
    return parsed


def main() -> None:
    questions = parse()
    OUTPUT.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = [q["id"] for q in questions if set(q["options"]) != {"A", "B", "C"}]
    print(f"questions: {len(questions)}")
    print(f"missing_options: {missing}")
    print(f"output: {OUTPUT}")


if __name__ == "__main__":
    main()
