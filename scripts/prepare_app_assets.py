import csv
import json
import re
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_QUESTIONS = ROOT / "data/questions_with_answers.json"
OCR_PAGES = ROOT / "sources/ocr"
PAGE_IMAGES = ROOT / "sources/ocr/pages"
PUBLIC_DATA = ROOT / "public/data"
PUBLIC_PAGES = ROOT / "public/exam-pages"
PUBLIC_CROPS = ROOT / "public/question-images"
SRC_DATA = ROOT / "src/data"

SPLIT_X = 1320
CROP_MARGIN_Y = 24
CROP_MARGIN_X = 90
CROP_MAX_WIDTH = 1200

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


def clean(text: str) -> str:
    text = text.replace("|", " ")
    text = text.replace("_", " ")
    text = text.replace("/", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .:-")


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


def page_lines(image: Path) -> list[dict]:
    output = subprocess.check_output(
        ["tesseract", str(image), "stdout", "-l", "pol", "--psm", "6", "tsv"],
        stderr=subprocess.DEVNULL,
        text=True,
    )
    rows = csv.DictReader(output.splitlines(), delimiter="\t")
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
        words = sorted(words, key=lambda word: word["left"])
        left_words = [word["text"] for word in words if word["left"] < SPLIT_X]
        right_words = [word["text"] for word in words if word["left"] >= SPLIT_X]
        result.append(
            {
                "top": min(word["top"] for word in words),
                "bottom": max(word["bottom"] for word in words),
                "left": min(word["left"] for word in words),
                "right": max(word["right"] for word in words),
                "left_text": clean(" ".join(left_words)),
                "right_text": clean(" ".join(right_words)),
            }
        )
    return sorted(result, key=lambda line: (line["top"], line["left"]))


def table_row_starts(image_path: Path) -> list[int]:
    with Image.open(image_path) as image:
        grayscale = image.convert("L")
        candidates: list[int] = []
        for y in range(200, grayscale.height - 100):
            row = grayscale.crop((CROP_MARGIN_X, y, SPLIT_X, y + 1))
            dark_pixels = sum(1 for pixel in row.tobytes() if pixel < 210)
            if dark_pixels > 700:
                candidates.append(y)

    groups: list[list[int]] = []
    for y in candidates:
        if not groups or y - groups[-1][-1] > 3:
            groups.append([y])
        else:
            groups[-1].append(y)

    return [(group[0] + group[-1]) // 2 for group in groups]


def fill_missing_question_starts(
    expected_ids: list[int], ocr_starts: dict[int, int], row_starts: list[int]
) -> dict[int, int]:
    starts = dict(ocr_starts)
    if not row_starts:
        return starts

    expected_index = {question_id: index for index, question_id in enumerate(expected_ids)}
    anchored_rows: dict[int, int] = {}
    used_rows: set[int] = set()
    for question_id, top in ocr_starts.items():
        nearest_index = min(range(len(row_starts)), key=lambda index: abs(row_starts[index] - top))
        if abs(row_starts[nearest_index] - top) <= 90:
            anchored_rows[question_id] = nearest_index
            used_rows.add(nearest_index)

    if not anchored_rows and len(row_starts) >= len(expected_ids):
        return dict(zip(expected_ids, row_starts[-len(expected_ids) :]))

    for question_id in expected_ids:
        if question_id in starts:
            continue

        question_index = expected_index[question_id]
        previous_anchors = [
            (expected_index[known_id], row_index)
            for known_id, row_index in anchored_rows.items()
            if expected_index[known_id] < question_index
        ]
        next_anchors = [
            (expected_index[known_id], row_index)
            for known_id, row_index in anchored_rows.items()
            if expected_index[known_id] > question_index
        ]

        candidate_index = None
        if previous_anchors:
            previous_question_index, previous_row_index = max(previous_anchors)
            candidate_index = previous_row_index + question_index - previous_question_index
        if (
            candidate_index is None
            or candidate_index >= len(row_starts)
            or candidate_index in used_rows
        ) and next_anchors:
            next_question_index, next_row_index = min(next_anchors)
            candidate_index = next_row_index - (next_question_index - question_index)

        if candidate_index is None or not 0 <= candidate_index < len(row_starts) or candidate_index in used_rows:
            continue

        starts[question_id] = row_starts[candidate_index]
        anchored_rows[question_id] = candidate_index
        used_rows.add(candidate_index)

    return starts


def build_question_bounds(page_map: dict[int, int]) -> dict[int, tuple[int, int]]:
    bounds: dict[int, tuple[int, int]] = {}
    expected_ids_by_page: dict[int, list[int]] = {}
    for question_id, page_number in page_map.items():
        expected_ids_by_page.setdefault(page_number, []).append(question_id)

    for image_path in sorted(PAGE_IMAGES.glob("page-*.png")):
        match = re.search(r"page-(\d+)\.png$", image_path.name)
        if not match:
            continue
        page_number = int(match.group(1))
        expected_ids = sorted(expected_ids_by_page.get(page_number, []))
        if not expected_ids:
            continue
        with Image.open(image_path) as image:
            page_height = image.height

        ocr_starts: dict[int, int] = {}
        for line in page_lines(image_path):
            match = re.match(r"^(\d{1,3})[,.]\s*", line["left_text"])
            if not match:
                continue
            question_id = int(match.group(1))
            if page_map.get(question_id) == page_number:
                ocr_starts[question_id] = line["top"]

        filled_starts = fill_missing_question_starts(expected_ids, ocr_starts, table_row_starts(image_path))
        starts = sorted(filled_starts.items(), key=lambda item: item[1])

        for index, (question_id, top) in enumerate(starts):
            next_top = starts[index + 1][1] if index + 1 < len(starts) else page_height - 120
            crop_top = max(0, top - CROP_MARGIN_Y)
            crop_bottom = min(page_height, max(crop_top + 180, next_top - CROP_MARGIN_Y))
            bounds[question_id] = (crop_top, crop_bottom)
    return bounds


def has_visual_prompt(question: str) -> bool:
    lowered = question.lower()
    return any(hint in lowered for hint in IMAGE_HINTS)


def prepare_questions() -> list[dict]:
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    SRC_DATA.mkdir(parents=True, exist_ok=True)
    page_map = build_page_map()
    question_bounds = build_question_bounds(page_map)
    questions = json.loads(SOURCE_QUESTIONS.read_text(encoding="utf-8"))
    for question in questions:
        page = page_map.get(question["id"])
        question["page"] = page
        question["has_visual_reference"] = bool(page and has_visual_prompt(question["question"]))
        question["page_image"] = f"exam-pages/page-{page:02d}.jpg" if question["has_visual_reference"] else None
        question["visual_image"] = (
            f"question-images/question-{question['id']:03d}.jpg"
            if question["has_visual_reference"] and question["id"] in question_bounds
            else None
        )
    payload = json.dumps(questions, ensure_ascii=False, indent=2) + "\n"
    (PUBLIC_DATA / "questions.json").write_text(payload, encoding="utf-8")
    (SRC_DATA / "questions.json").write_text(payload, encoding="utf-8")
    missing_pages = [q["id"] for q in questions if q["page"] is None]
    visual_count = sum(1 for q in questions if q["has_visual_reference"])
    crop_count = sum(1 for q in questions if q["visual_image"])
    print(f"questions: {len(questions)}")
    print(f"missing_page_map: {missing_pages}")
    print(f"visual_reference_questions: {visual_count}")
    print(f"visual_question_crops: {crop_count}")
    return questions


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


def prepare_question_crops(questions: list[dict]) -> None:
    PUBLIC_CROPS.mkdir(parents=True, exist_ok=True)
    for old_crop in PUBLIC_CROPS.glob("question-*.jpg"):
        old_crop.unlink()

    page_map = {question["id"]: question["page"] for question in questions if question["page"]}
    question_bounds = build_question_bounds(page_map)
    crops_written = 0

    for question in questions:
        output_path = question.get("visual_image")
        page = question.get("page")
        bounds = question_bounds.get(question["id"])
        if not output_path or not page or not bounds:
            continue

        image_path = PAGE_IMAGES / f"page-{page:02d}.png"
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            top, bottom = bounds
            crop = image.crop((CROP_MARGIN_X, top, image.width - CROP_MARGIN_X, bottom))
            if crop.width > CROP_MAX_WIDTH:
                ratio = CROP_MAX_WIDTH / crop.width
                crop = crop.resize((CROP_MAX_WIDTH, int(crop.height * ratio)))
            crop.save(ROOT / "public" / output_path, "JPEG", quality=88, optimize=True)
            crops_written += 1

    print(f"question_crops: {crops_written}")


def main() -> None:
    questions = prepare_questions()
    prepare_page_images()
    prepare_question_crops(questions)


if __name__ == "__main__":
    main()
