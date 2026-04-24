import pandas as pd
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV = os.path.join(BASE_DIR, "data", "projects.csv")

OUTPUT_KEYWORDS = os.path.join(BASE_DIR, "data", "keywords.json")
OUTPUT_MINISTRY = os.path.join(BASE_DIR, "data", "ministry_keywords.json")

# 텍스트 정리 함수
def clean_text(text):
    text = re.sub(r'[^가-힣a-zA-Z ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# 데이터 로드
df = pd.read_csv(INPUT_CSV)

# 텍스트 전처리
documents = df["content"].fillna("").apply(clean_text).tolist()

# TF-IDF
vectorizer = TfidfVectorizer(max_features=50)
X = vectorizer.fit_transform(documents)

keywords = vectorizer.get_feature_names_out()
scores = X.sum(axis=0).A1

keyword_data = sorted(
    [{"keyword": k, "score": float(s)} for k, s in zip(keywords, scores)],
    key=lambda x: x["score"],
    reverse=True
)

# 전체 키워드 저장
with open(OUTPUT_KEYWORDS, "w", encoding="utf-8") as f:
    json.dump(keyword_data, f, ensure_ascii=False, indent=2)

# 부처별 키워드
ministry_data = {}

for ministry in df["ministry"].unique():
    sub_docs = df[df["ministry"] == ministry]["content"].fillna("").apply(clean_text)

    if len(sub_docs) < 2:
        continue

    vec = TfidfVectorizer(max_features=20)
    X_sub = vec.fit_transform(sub_docs)

    kw = vec.get_feature_names_out()
    sc = X_sub.sum(axis=0).A1

    ministry_data[ministry] = sorted(
        [{"keyword": k, "score": float(s)} for k, s in zip(kw, sc)],
        key=lambda x: x["score"],
        reverse=True
    )

# 저장
with open(OUTPUT_MINISTRY, "w", encoding="utf-8") as f:
    json.dump(ministry_data, f, ensure_ascii=False, indent=2)

print("키워드 분석 완료")