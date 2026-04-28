import os
import re
import json
import pdfplumber
import pandas as pd
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "pdfs", "full")

OUTPUT_CSV = os.path.join(BASE_DIR, "data", "projects_full.csv")
OUTPUT_JSON = os.path.join(BASE_DIR, "data", "projects_full.json")

STANDARD_MINISTRIES = [
    "감사원", "개인정보위원회", "경찰청", "고용노동부", "과학기술정보통신부",
    "관세청", "교육부", "국가데이터처", "국가유산청", "국민권익위원회",
    "국방부", "국세청", "국토교통부", "금융위원회", "기상청",
    "기획예산처", "기후에너지환경부", "농립축산식품부", "농촌진흥청",
    "대법원", "문화체육관광부", "방송미디어통신위원회", "방위사업청",
    "법무부", "법제처", "병무청", "보건복지부", "산림청",
    "산업통상부", "소방청", "식품의약품안전처", "우주항공청",
    "인사혁신처", "조달청", "중소벤처기업부", "지식재산처",
    "질병관리청", "해양경찰청", "해양수산부", "행정안전부"
]

MINISTRY_MAP = {
    "산업통상자원부": "산업통상부",
    "산업통산부": "산업통상부",
    "중소기업벤처부": "중소벤처기업부",
    "농림축산식품부": "농립축산식품부",
    "환경부": "기후에너지환경부",
    "방송통신위원회": "방송미디어통신위원회",
    "행정안저부": "행정안전부"
}

def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def normalize_text(text):
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def split_projects(text):
    text = normalize_text(text)

    parts = re.split(
        r"(?:^|\n)\s*(?:[-–—]\s*)?\d*\s*[-]?\s*사\s*업\s*명\s*\n?",
        text
    )

    projects = []
    for part in parts:
        part = part.strip()
        if len(part) < 300:
            continue
        if "예산 총괄표" in part or "지출계획 총괄표" in part or "사업 코드 정보" in part:
            projects.append(part)

    return projects

def clean_project_name(name):
    name = re.sub(r"\s+", " ", str(name)).strip()
    name = name.replace("□", "").strip()
    return name

def get_project_name(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:15]:
        if "□" in line:
            continue
        if "사업 코드 정보" in line:
            continue
        if "구분" in line and "회계" in line:
            continue
        if len(line) >= 3:
            return clean_project_name(line)

    return "unknown"

def get_ministry(text, filename):
    for std in STANDARD_MINISTRIES:
        if filename.startswith(std):
            return std

    for raw, mapped in MINISTRY_MAP.items():
        if raw in filename:
            return mapped

    for raw, mapped in MINISTRY_MAP.items():
        if raw in text:
            return mapped

    for std in STANDARD_MINISTRIES:
        if std in text:
            return std

    return "기타"

def get_account_type(text):
    if "특별회계" in text:
        return "특별회계"
    if "기금" in text or "전력산업기반기금" in text:
        return "기금"
    if "일반회계" in text:
        return "일반회계"
    return "기타"

def get_category(text):
    if "R&D" in text or "연구개발" in text:
        return "R&D"
    if "정보화" in text:
        return "정보화"
    return "일반"

def get_project_status(text):
    head = "\n".join(text.splitlines()[:40])

    if re.search(r"신규\s*계속\s*완료", head):
        if "○" in head or "O" in head:
            first_mark_area = head.split("신규 계속 완료")[1] if "신규 계속 완료" in head else head
            if first_mark_area.strip().startswith(("○", "O")):
                return "신규"

    if "순증" in text or "(2025) 0백만원" in text or "2025)0백만원" in text:
        return "신규"

    return "계속"

def extract_budget_table_line(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if ("2024년" in line and "2025년" in line and "2026년" in line) or "예산 총괄표" in line or "지출계획 총괄표" in line:
            block = " ".join(lines[i:i + 8])
            return block

    return " ".join(lines[:20])

def extract_numbers(text):
    nums = re.findall(r"△?\d{1,3}(?:,\d{3})+|△?\d+", text)
    cleaned = []

    for n in nums:
        negative = n.startswith("△")
        n = n.replace("△", "").replace(",", "")
        try:
            value = int(n)
            if negative:
                value *= -1
            cleaned.append(value)
        except ValueError:
            pass

    return cleaned

def extract_budget_values(text):
    table_line = extract_budget_table_line(text)
    nums = extract_numbers(table_line)

    nums = [n for n in nums if abs(n) >= 10]

    result = {
        "budget_2024": 0,
        "budget_2025": 0,
        "request_2026": 0,
        "budget_2026": 0,
        "change_amount": 0,
        "change_rate": 0.0
    }

    # 가장 일반적인 총괄표 구조:
    # 2024 결산 / 2025 본예산 / 추경(A) / 2026 요구안 / 본예산(B) / 증감 / 증감률
    if len(nums) >= 5:
        candidates = [n for n in nums if abs(n) < 10000000]

        if len(candidates) >= 5:
            result["budget_2024"] = candidates[0]
            result["budget_2025"] = candidates[1]

            if len(candidates) >= 6:
                result["request_2026"] = candidates[3]
                result["budget_2026"] = candidates[4]
                result["change_amount"] = candidates[5] if len(candidates) >= 6 else result["budget_2026"] - result["budget_2025"]
            else:
                result["request_2026"] = candidates[-2]
                result["budget_2026"] = candidates[-1]
                result["change_amount"] = result["budget_2026"] - result["budget_2025"]

    if result["budget_2026"] == 0:
        m = re.search(r"2026[^0-9△]*(?:예산|본예산|확정|조정|계획)?[^0-9△]*(△?\d{1,3}(?:,\d{3})+|△?\d+)", text)
        if m:
            result["budget_2026"] = int(m.group(1).replace("△", "-").replace(",", ""))

    if result["budget_2025"] and result["budget_2026"]:
        result["change_amount"] = result["budget_2026"] - result["budget_2025"]
        result["change_rate"] = round((result["change_amount"] / result["budget_2025"]) * 100, 2)
    elif result["budget_2026"] and not result["budget_2025"]:
        result["change_amount"] = result["budget_2026"]
        result["change_rate"] = 999.0

    return result

def infer_domain(text):
    t = str(text)

    domain_rules = [
        ("제조/스마트팩토리", ["제조", "스마트공장", "산업AI", "공정", "품질", "로봇"]),
        ("의료/바이오", ["바이오", "의료", "의약", "질환", "치료제", "신약", "헬스"]),
        ("공공행정/전자정부", ["전자정부", "공공데이터", "행정", "민원", "정부", "감사", "등기"]),
        ("안전/치안/재난", ["재난", "치안", "경찰", "소방", "군중", "안전", "긴급상황"]),
        ("국방/방산", ["국방", "방위", "민군", "무인", "주파수", "전장"]),
        ("교통/물류/스마트시티", ["교통", "물류", "스마트시티", "항공", "관제", "AIoT", "도시"]),
        ("에너지/환경/기후", ["에너지", "전력", "탄소중립", "환경", "기후", "ESS", "재생에너지"]),
        ("농림/식품", ["농림", "농업", "농작업", "농촌", "식품", "산림"]),
        ("해양/수산", ["해양", "해저", "수산", "해상", "선박"]),
        ("교육/문화/콘텐츠", ["교육", "문화", "콘텐츠", "XR", "디지털콘텐츠"]),
        ("데이터/플랫폼", ["데이터", "빅데이터", "플랫폼", "정보시스템", "클라우드"]),
        ("AI인프라/컴퓨팅", ["컴퓨팅", "디지털트윈", "반도체", "GPU", "클라우드", "AX"]),
    ]

    for domain, keywords in domain_rules:
        if any(k in t for k in keywords):
            return domain

    return "기타"

def extract_purpose(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    capture = False
    selected = []

    for line in lines:
        if "사업목적" in line or "사업목적·내용" in line or "사업목적･내용" in line:
            capture = True
            continue

        if capture:
            if "사업개요" in line or "사업근거" in line:
                break
            selected.append(line)

        if len(selected) >= 5:
            break

    return " ".join(selected)[:800]

def main():
    if not os.path.exists(PDF_DIR):
        raise FileNotFoundError(f"PDF 폴더가 없습니다: {PDF_DIR}")

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        raise FileNotFoundError(f"PDF 파일이 없습니다: {PDF_DIR}")

    rows = []

    for filename in tqdm(pdf_files, desc="통합 PDF 사업 추출 중"):
        pdf_path = os.path.join(PDF_DIR, filename)
        full_text = extract_text(pdf_path)
        projects = split_projects(full_text)

        for idx, project_text in enumerate(projects, start=1):
            budget = extract_budget_values(project_text)

            row = {
                "source_file": filename,
                "project_index": idx,
                "ministry": get_ministry(project_text, filename),
                "project_name": get_project_name(project_text),
                "category": get_category(project_text),
                "account_type": get_account_type(project_text),
                "status": get_project_status(project_text),
                "domain": infer_domain(project_text),
                "budget_2024": budget["budget_2024"],
                "budget_2025": budget["budget_2025"],
                "request_2026": budget["request_2026"],
                "budget_2026": budget["budget_2026"],
                "change_amount": budget["change_amount"],
                "change_rate": budget["change_rate"],
                "purpose": extract_purpose(project_text),
                "content": project_text[:3000]
            }

            rows.append(row)

    df = pd.DataFrame(rows)

    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print("완료:", OUTPUT_CSV)
    print("완료:", OUTPUT_JSON)
    print("총 사업 수:", len(df))
    print("참여 부처 수:", df["ministry"].nunique())
    print("총 2026 예산:", f'{int(df["budget_2026"].sum()):,} 백만원')

if __name__ == "__main__":
    main()