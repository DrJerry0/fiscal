import os
import re
import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

INPUT = os.path.join(DATA_DIR, "projects_full.csv")

OUTPUT_MINISTRY = os.path.join(DATA_DIR, "ministry_analysis.json")
OUTPUT_DOMAIN = os.path.join(DATA_DIR, "domain_analysis.json")
OUTPUT_SIMILARITY = os.path.join(DATA_DIR, "similarity_analysis.json")


KOREAN_STOPWORDS = [
    "사업", "예산", "지원", "구축", "운영", "개발", "기반", "추진", "관리",
    "활용", "고도화", "확대", "강화", "제공", "수행", "위한", "통한",
    "및", "등", "관련", "해당", "대상", "분야", "기술", "정보", "시스템",
    "서비스", "데이터", "인공지능", "AI", "ai", "2024", "2025", "2026",
    "백만원", "본예산", "추경", "요구안", "확정", "결산", "증감"
]


def clean_text(text):
    text = str(text)
    text = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def to_records(series):
    return [
        {"label": str(k), "value": float(v)}
        for k, v in series.items()
    ]


def safe_num(df, col):
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def build_ministry_analysis(df):
    rows = []

    ministries = sorted(df["ministry"].dropna().unique())

    for ministry in ministries:
        sub = df[df["ministry"] == ministry]

        category_dist = (
            sub.groupby("category")["project_name"]
            .count()
            .sort_values(ascending=False)
            .to_dict()
        )

        domain_dist = (
            sub.groupby("domain")["budget_2026"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .to_dict()
        )

        top_projects = (
            sub.sort_values("budget_2026", ascending=False)
            .head(10)[
                [
                    "project_name", "domain", "category",
                    "budget_2026", "change_amount", "change_rate"
                ]
            ]
            .to_dict(orient="records")
        )

        rows.append({
            "ministry": ministry,
            "project_count": int(len(sub)),
            "total_budget": int(sub["budget_2026"].sum()),
            "avg_budget": float(round(sub["budget_2026"].mean(), 2)) if len(sub) else 0,
            "rd_count": int((sub["category"] == "R&D").sum()),
            "informatization_count": int((sub["category"] == "정보화").sum()),
            "general_count": int((sub["category"] == "일반").sum()),
            "new_count": int((sub["status"] == "신규").sum()),
            "continue_count": int((sub["status"] == "계속").sum()),
            "category_distribution": category_dist,
            "domain_budget_top10": domain_dist,
            "top_projects": top_projects
        })

    summary = {
        "total_ministries": int(df["ministry"].nunique()),
        "ministry_project_count": to_records(
            df.groupby("ministry")["project_name"].count().sort_values(ascending=False)
        ),
        "ministry_budget": to_records(
            df.groupby("ministry")["budget_2026"].sum().sort_values(ascending=False)
        ),
        "ministry_avg_budget": to_records(
            df.groupby("ministry")["budget_2026"].mean().sort_values(ascending=False)
        ),
        "items": rows
    }

    return summary


def build_domain_analysis(df):
    rows = []

    domains = sorted(df["domain"].dropna().unique())

    for domain in domains:
        sub = df[df["domain"] == domain]

        ministry_budget = (
            sub.groupby("ministry")["budget_2026"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .to_dict()
        )

        ministry_count = (
            sub.groupby("ministry")["project_name"]
            .count()
            .sort_values(ascending=False)
            .head(10)
            .to_dict()
        )

        status_dist = (
            sub.groupby("status")["project_name"]
            .count()
            .sort_values(ascending=False)
            .to_dict()
        )

        category_dist = (
            sub.groupby("category")["project_name"]
            .count()
            .sort_values(ascending=False)
            .to_dict()
        )

        top_projects = (
            sub.sort_values("budget_2026", ascending=False)
            .head(10)[
                [
                    "project_name", "ministry", "category",
                    "budget_2026", "change_amount", "change_rate"
                ]
            ]
            .to_dict(orient="records")
        )

        rows.append({
            "domain": domain,
            "project_count": int(len(sub)),
            "total_budget": int(sub["budget_2026"].sum()),
            "avg_budget": float(round(sub["budget_2026"].mean(), 2)) if len(sub) else 0,
            "ministry_budget_top10": ministry_budget,
            "ministry_count_top10": ministry_count,
            "status_distribution": status_dist,
            "category_distribution": category_dist,
            "top_projects": top_projects
        })

    ministry_domain_matrix = (
        df.pivot_table(
            index="ministry",
            columns="domain",
            values="budget_2026",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
        .to_dict(orient="records")
    )

    summary = {
        "total_domains": int(df["domain"].nunique()),
        "domain_project_count": to_records(
            df.groupby("domain")["project_name"].count().sort_values(ascending=False)
        ),
        "domain_budget": to_records(
            df.groupby("domain")["budget_2026"].sum().sort_values(ascending=False)
        ),
        "ministry_domain_matrix": ministry_domain_matrix,
        "items": rows
    }

    return summary


def build_similarity_analysis(df):
    work = df.copy()
    work["similarity_text"] = (
        work["project_name"].fillna("") + " " +
        work["domain"].fillna("") + " " +
        work["category"].fillna("") + " " +
        work["purpose"].fillna("") + " " +
        work["content"].fillna("")
    ).apply(clean_text)

    # 너무 짧은 문서는 제외
    work = work[work["similarity_text"].str.len() >= 30].reset_index(drop=True)

    if len(work) < 2:
        return {
            "top_pairs": [],
            "network_nodes": [],
            "network_edges": [],
            "message": "유사성 분석에 필요한 문서 수가 부족합니다."
        }

    vectorizer = TfidfVectorizer(
        max_features=1200,
        min_df=2,
        max_df=0.85,
        stop_words=KOREAN_STOPWORDS,
        ngram_range=(1, 2)
    )

    matrix = vectorizer.fit_transform(work["similarity_text"])
    sim = cosine_similarity(matrix)

    pairs = []

    for i in range(len(work)):
        for j in range(i + 1, len(work)):
            score = float(sim[i, j])

            if score >= 0.18:
                pairs.append({
                    "source_index": int(i),
                    "target_index": int(j),
                    "source_project": work.loc[i, "project_name"],
                    "target_project": work.loc[j, "project_name"],
                    "source_ministry": work.loc[i, "ministry"],
                    "target_ministry": work.loc[j, "ministry"],
                    "source_domain": work.loc[i, "domain"],
                    "target_domain": work.loc[j, "domain"],
                    "similarity": round(score, 4)
                })

    pairs = sorted(pairs, key=lambda x: x["similarity"], reverse=True)

    top_pairs = pairs[:100]

    # 네트워크는 너무 커지지 않게 상위 60개 pair 기준
    network_pairs = top_pairs[:60]

    node_ids = set()
    for p in network_pairs:
        node_ids.add(p["source_index"])
        node_ids.add(p["target_index"])

    nodes = []
    for idx in sorted(node_ids):
        row = work.loc[idx]
        nodes.append({
            "id": int(idx),
            "label": str(row["project_name"])[:40],
            "ministry": row["ministry"],
            "domain": row["domain"],
            "budget_2026": int(row["budget_2026"])
        })

    edges = [
        {
            "source": p["source_index"],
            "target": p["target_index"],
            "weight": p["similarity"]
        }
        for p in network_pairs
    ]

    # 키워드 추출
    feature_names = vectorizer.get_feature_names_out()
    tfidf_scores = matrix.sum(axis=0).A1

    keywords = sorted(
        [
            {"keyword": str(k), "score": float(s)}
            for k, s in zip(feature_names, tfidf_scores)
        ],
        key=lambda x: x["score"],
        reverse=True
    )[:100]

    result = {
        "document_count": int(len(work)),
        "similarity_threshold": 0.18,
        "top_pairs": top_pairs,
        "network_nodes": nodes,
        "network_edges": edges,
        "keywords": keywords
    }

    return result


def main():
    df = pd.read_csv(INPUT).fillna("")

    for col in [
        "budget_2024", "budget_2025", "request_2026",
        "budget_2026", "change_amount", "change_rate"
    ]:
        if col in df.columns:
            df = safe_num(df, col)

    for col in ["ministry", "domain", "category", "status", "project_name", "purpose", "content"]:
        if col not in df.columns:
            df[col] = ""

    ministry_analysis = build_ministry_analysis(df)
    domain_analysis = build_domain_analysis(df)
    similarity_analysis = build_similarity_analysis(df)

    with open(OUTPUT_MINISTRY, "w", encoding="utf-8") as f:
        json.dump(ministry_analysis, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DOMAIN, "w", encoding="utf-8") as f:
        json.dump(domain_analysis, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_SIMILARITY, "w", encoding="utf-8") as f:
        json.dump(similarity_analysis, f, ensure_ascii=False, indent=2)

    print("완료:", OUTPUT_MINISTRY)
    print("완료:", OUTPUT_DOMAIN)
    print("완료:", OUTPUT_SIMILARITY)
    print("부처 수:", ministry_analysis["total_ministries"])
    print("분야 수:", domain_analysis["total_domains"])
    print("유사도 문서 수:", similarity_analysis.get("document_count", 0))
    print("유사 사업 쌍:", len(similarity_analysis.get("top_pairs", [])))


if __name__ == "__main__":
    main()