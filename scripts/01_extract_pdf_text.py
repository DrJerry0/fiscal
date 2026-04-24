import os
import pdfplumber
import pandas as pd
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "pdfs", "sample")
OUTPUT_CSV = os.path.join(BASE_DIR, "data", "projects.csv")

MINISTRIES = [
    "과학기술정보통신부", "산업통상부", "중소벤처기업부",
    "행정안전부", "국토교통부", "농림축산식품부",
    "해양수산부", "질병관리청", "경찰청", "외교부"
]

def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def detect_ministry(text, filename):
    # 1순위: 파일명 기준 (가장 정확)
    for ministry in MINISTRIES:
        if filename.startswith(ministry):
            return ministry

    # 2순위: 텍스트 기준
    for ministry in MINISTRIES:
        if ministry in text:
            return ministry

    return ""

def detect_category(text, filename):
    if "R&D" in text or "R%26D" in filename:
        return "R&D"
    if "정보화" in text or "정보화" in filename:
        return "정보화"
    return "일반"

def parse_project_name(text, filename):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines[:20]):
        if "사업명" in line:
            if i + 1 < len(lines):
                return lines[i + 1].replace("□", "").strip()
            return line.replace("사업명", "").strip()
    return os.path.splitext(filename)[0]

rows = []

pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]

for filename in tqdm(pdf_files, desc="PDF 추출 중"):
    pdf_path = os.path.join(PDF_DIR, filename)
    text = extract_text(pdf_path)

    rows.append({
        "file": filename,
        "ministry": detect_ministry(text, filename),
        "project_name": parse_project_name(text, filename),
        "category": detect_category(text, filename),
        "text_length": len(text),
        "content": text[:3000]
    })

df = pd.DataFrame(rows)
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print(f"완료: {OUTPUT_CSV}")
print(f"총 PDF 수: {len(df)}")