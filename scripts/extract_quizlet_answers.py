import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/quizlet_api_raw.json"
OUTPUT = ROOT / "data/questions_with_answers.json"
OUTPUT_ALL = ROOT / "data/quizlet_338_raw.json"

OPTION_OVERRIDES = {
    107: {
        "A": "Znakiem nr 1",
        "B": "Znakiem nr 2",
        "C": "Znakiem nr 3",
    }
}


def category_for(number: int) -> str:
    if number <= 57:
        return "Budowa jachtów"
    if number <= 100:
        return "Eksploatacja oraz manewrowanie jachtem"
    if number <= 148:
        return "Podstawy locji i pomoce nawigacyjne"
    if number <= 195:
        return "Przepisy prawa drogi, ochrona wód i etykieta jachtowa"
    if number <= 230:
        return "Teoria żeglowania"
    if number <= 255:
        return "Wiadomości z zakresu meteorologii"
    return "Wiadomości z zakresu ratownictwa wodnego"


def plain_media(side: dict) -> str:
    media = side.get("media") or []
    if not media:
        return ""
    return media[0].get("plainText", "").strip()


def parse_prompt(prompt: str) -> tuple[int, str, dict[str, str]]:
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    first = lines[0]
    match = re.match(r"^(\d+)\.\s*(.*)$", first)
    if not match:
        raise ValueError(f"Cannot parse question number from: {first!r}")
    number = int(match.group(1))
    question_lines = [match.group(2).strip()]
    options: dict[str, str] = {}
    current = None

    for line in lines[1:]:
        option = re.match(r"^([ABC]):\s*(.*)$", line)
        if option:
            current = option.group(1)
            options[current] = option.group(2).strip()
        elif current:
            options[current] += " " + line
        else:
            question_lines.append(line)

    question = " ".join(question_lines).strip()
    return number, question, options


def answer_letter(answer: str) -> str:
    match = re.match(r"^([ABC]):", answer.strip())
    if not match:
        raise ValueError(f"Cannot parse answer letter from: {answer!r}")
    return match.group(1)


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    items = data["responses"][0]["models"]["studiableItem"]

    rows = []
    for item in items:
        sides = item["cardSides"]
        answer = plain_media(sides[0])
        prompt = plain_media(sides[1])
        if not answer or not prompt:
            continue
        try:
            number, question, options = parse_prompt(prompt)
            options = OPTION_OVERRIDES.get(number, options)
            correct = answer_letter(answer)
        except ValueError:
            continue

        rows.append(
            {
                "id": number,
                "category": category_for(number),
                "question": question,
                "options": options,
                "correct": correct,
                "correct_answer": options.get(correct, answer.removeprefix(f"{correct}:").strip()),
                "source": {
                    "questions": "PZŻ / KanaJacht PDF",
                    "answer_key": "Quizlet public flashcard set 1061896430",
                },
            }
        )

    rows = sorted(rows, key=lambda row: row["id"])
    OUTPUT_ALL.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    official = [row for row in rows if 1 <= row["id"] <= 301]
    OUTPUT.write_text(json.dumps(official, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    missing_ids = sorted(set(range(1, 302)) - {row["id"] for row in official})
    bad_options = [row["id"] for row in official if set(row["options"]) != {"A", "B", "C"}]
    print(f"quizlet_rows: {len(rows)}")
    print(f"official_rows: {len(official)}")
    print(f"missing_ids: {missing_ids}")
    print(f"bad_options: {bad_options}")
    print(f"output: {OUTPUT}")


if __name__ == "__main__":
    main()
