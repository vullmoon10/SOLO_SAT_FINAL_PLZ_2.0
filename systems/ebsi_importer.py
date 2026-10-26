"""Import locally downloaded EBSi exam PDFs into the booth's reviewed question bank.

The EBSi archive currently requires a signed-in browser for its download action;
this importer deliberately does not automate login or bypass that check.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from network.server import BoothDatabase, DATA_DIR


ALLOWED_SUBJECTS = {"국어", "수학", "영어", "한국사", "통합사회", "통합과학",
                    "사회", "과학", "생활과윤리", "윤리와사상", "한국지리", "세계지리",
                    "동아시아사", "세계사", "경제", "정치와법", "사회문화", "물리학", "화학", "생명과학", "지구과학"}


def _resolve_import(path: str) -> Path:
    root = (DATA_DIR / "imports").resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"PDF는 관리자 데이터 폴더 안에 두세요: {root}") from exc
    if candidate.suffix.lower() != ".pdf" or not candidate.is_file():
        raise ValueError("선택한 PDF 파일을 찾을 수 없습니다.")
    return candidate


def _answers_from_pdf(doc):
    text = "\n".join(page.get_text() for page in doc)
    pairs = {}
    for match in re.finditer(r"(?<!\d)(\d{1,2})\s*[-.)]?[ \t]*([①②③④⑤])", text):
        pairs[int(match.group(1))] = "①②③④⑤".index(match.group(2))
    if not pairs:
        # EBSi answer tables often put the answer mark on the next text line.
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines[:-1]):
            number = re.fullmatch(r"\d{1,2}", line)
            answer = re.fullmatch(r"[①②③④⑤]", lines[index + 1])
            if number and answer:
                pairs[int(line)] = "①②③④⑤".index(lines[index + 1])
    return pairs


def _find_two_point_questions(doc, subject):
    found = []
    number_patterns = (re.compile(r"(?<!\d)(\d{1,2})\s*[.)]"), re.compile(r"(?<!\d)(\d{1,2})\s*번"))
    for page_index, page in enumerate(doc):
        text = page.get_text("text")
        # Keep only explicit 2-point markers; uncertain text extraction must be reviewed by an administrator.
        for match in re.finditer(r"(?<!\d)(\d{1,2})(?:\s*(?:번|[.)]))?\s*(?:\[|\()?\s*2\s*점", text):
            question_no = int(match.group(1))
            if not 1 <= question_no <= 60:
                continue
            # English questions 1-17 depend on the listening audio, which is not imported yet.
            if subject == "영어" and question_no <= 17:
                continue
            prefix = text[max(0, match.start() - 80):match.start()]
            for pattern in number_patterns:
                anchors = list(pattern.finditer(prefix))
                if anchors:
                    question_no = int(anchors[-1].group(1))
            found.append((question_no, page_index, text[:1600]))
    # A question may have its point value repeated in extracted headers; retain one page per question.
    by_number = {}
    for item in found:
        by_number.setdefault(item[0], item)
    return list(by_number.values())


def sync_exam(year: int, subject: str, problem_pdf: str = "", answer_pdf: str = ""):
    if subject not in ALLOWED_SUBJECTS:
        raise ValueError("지원하지 않는 과목입니다.")
    if not 2006 <= year <= 2100:
        raise ValueError("학년도 값이 올바르지 않습니다.")
    problem_path, answer_path = _resolve_import(problem_pdf), _resolve_import(answer_pdf)
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF 처리를 위해 PyMuPDF 설치가 필요합니다. requirements.txt를 설치하세요.") from exc
    with fitz.open(problem_path) as problem_doc, fitz.open(answer_path) as answer_doc:
        answers = _answers_from_pdf(answer_doc)
        candidates = _find_two_point_questions(problem_doc, subject)
        questions = []
        digest = hashlib.sha256(problem_path.read_bytes()).hexdigest()[:12]
        for number, page_index, text in candidates:
            if number not in answers:
                continue
            page = problem_doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
            image = pix.tobytes("png")
            qid = f"{year}-{subject}-{number}-{digest}"
            questions.append((qid, year, subject, number, 2, answers[number], page_index, str(problem_path),
                              image, f"{year}년 3월 고1 {subject} {number}번 (PDF {page_index + 1}쪽)",
                              '["①", "②", "③", "④", "⑤"]', f"https://www.ebsi.co.kr/ebs/xip/xipc/previousPaperList.ebs?targetCd=D100"))
    if not questions:
        raise ValueError("2점 문항과 정답을 자동으로 연결하지 못했습니다. PDF 형식이나 정답표를 확인하세요.")
    db = BoothDatabase()
    with db.connect() as conn:
        conn.executemany("""INSERT OR REPLACE INTO questions
            (id,year,subject,question_no,score_value,answer,page,pdf_path,page_image,question_text,choices_json,source_url,reviewed)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0)""", questions)
    return {"imported": len(questions), "subject": subject, "year": year,
            "message": "가져온 문항은 관리자 확인 후 공개 처리해야 출제됩니다."}


def review_question(question_id: str, approved: bool):
    with BoothDatabase().connect() as db:
        cur = db.execute("UPDATE questions SET reviewed=? WHERE id=?", (int(approved), question_id))
        return cur.rowcount > 0
