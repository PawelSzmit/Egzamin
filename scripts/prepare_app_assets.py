import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_QUESTIONS = ROOT / "data/questions_with_answers.json"
OCR_PAGES = ROOT / "sources/ocr"
PAGE_IMAGES = ROOT / "sources/ocr/pages"
PUBLIC_DATA = ROOT / "public/data"
PUBLIC_PAGES = ROOT / "public/exam-pages"
SRC_DATA = ROOT / "src/data"

IMAGE_HINTS = (
    "rysunku",
    "rysunek",
    "szkicu",
    "obok",
    "pokazana",
    "pokazany",
    "pokazane",
    "diagram",
    "mapie",
    "tablica",
    "znak",
    "pława",
    "pławę",
    "boja",
)


def build_page_map() -> dict[int, int]:
    page_map: dict[int, int] = {}
    for path in sorted(OCR_PAGES.glob("page-*.txt")):
        match = re.search(r"page-(\d+)\.txt$", path.name)
        if not match:
            continue
        page_number = int(match.group(1))
        text = path.read_text(encoding="utf-8", errors="ignore")
        for question_id in re.findall(r"(?m)^(\d{1,3})[,.]", text):
            page_map.setdefault(int(question_id), page_number)
    return page_map


def has_visual_prompt(question: str) -> bool:
    lowered = question.lower()
    return any(hint in lowered for hint in IMAGE_HINTS)


def prepare_questions() -> None:
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    SRC_DATA.mkdir(parents=True, exist_ok=True)
    page_map = build_page_map()
    questions = json.loads(SOURCE_QUESTIONS.read_text(encoding="utf-8"))
    for question in questions:
        page = page_map.get(question["id"])
        question["page"] = page
        question["has_visual_reference"] = bool(page and has_visual_prompt(question["question"]))
        question["page_image"] = f"exam-pages/page-{page:02d}.jpg" if question["has_visual_reference"] else None
    payload = json.dumps(questions, ensure_ascii=False, indent=2) + "\n"
    (PUBLIC_DATA / "questions.json").write_text(payload, encoding="utf-8")
    (SRC_DATA / "questions.json").write_text(payload, encoding="utf-8")
    missing_pages = [q["id"] for q in questions if q["page"] is None]
    visual_count = sum(1 for q in questions if q["has_visual_reference"])
    print(f"questions: {len(questions)}")
    print(f"missing_page_map: {missing_pages}")
    print(f"visual_reference_questions: {visual_count}")


def prepare_page_images() -> None:
    PUBLIC_PAGES.mkdir(parents=True, exist_ok=True)
    for image_path in sorted(PAGE_IMAGES.glob("page-*.png")):
        match = re.search(r"page-(\d+)\.png$", image_path.name)
        if not match:
            continue
        page_number = int(match.group(1))
        output = PUBLIC_PAGES / f"page-{page_number:02d}.jpg"
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            width = 1100
            ratio = width / image.width
            resized = image.resize((width, int(image.height * ratio)))
            resized.save(output, "JPEG", quality=82, optimize=True)
    print(f"page_images: {len(list(PUBLIC_PAGES.glob('*.jpg')))}")


def main() -> None:
    prepare_questions()
    prepare_page_images()


if __name__ == "__main__":
    main()
