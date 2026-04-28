import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE_DIR, "data", "projects_full.csv")
DATA_DIR = os.path.join(BASE_DIR, "data")

OUTPUT_OVERVIEW = os.path.join(DATA_DIR, "overview_summary.json")
OUTPUT_CHARTS = os.path.join(DATA_DIR, "dashboard_charts.json")
OUTPUT_RECS = os.path.join(DATA_DIR, "policy_recommendations.json")

def to_records(series):
    return [
        {"label": str(k), "value": float(v)}
        for k, v in series.items()
    ]

def main():
    df = pd.read_csv(INPUT).fillna("")

    numeric_cols = [
        "budget_2024", "budget_2025", "request_2026",
        "budget_2026", "change_amount", "change_rate"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    total_projects = len(df)
    total_budget = int(df["budget_2026"].sum())
    total_ministries = df["ministry"].nunique()
    total_domains = df["domain"].nunique()

    # 정책축은 현재 3축으로 고정: 기술혁신, 산업확산, 공공서비스
    policy_axes = 3

    recommendations = []

    for _, row in df.iterrows():
        title = str(row["project_name"])[:60]
        ministry = row["ministry"]
        domain = row["domain"]
        change_rate = row["change_rate"]
        budget = row["budget_2026"]

        priority = "일반"
        due_status = "정상"

        if change_rate < -20:
            priority = "예산감소 점검"
            due_status = "기한임박"
        elif budget >= 50000:
            priority = "대형사업 관리"
        elif row["status"] == "신규":
            priority = "신규사업 성과체계 필요"

        recommendations.append({
            "title": f"{title} 정책 점검",
            "ministry": ministry,
            "domain": domain,
            "priority": priority,
            "due_status": due_status,
            "budget_2026": int(budget),
            "change_rate": float(change_rate)
        })

    urgent_count = sum(
        1 for r in recommendations
        if r["due_status"] in ["기한임박", "초과"]
    )

    overview = {
        "total_projects": total_projects,
        "total_budget": total_budget,
        "total_ministries": total_ministries,
        "strategy_fields": total_domains,
        "policy_axes": policy_axes,
        "policy_recommendations": len(recommendations),
        "urgent_or_overdue": urgent_count
    }

    ministry_budget = (
        df.groupby("ministry")["budget_2026"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    project_type = (
        df.groupby("category")["project_name"]
        .count()
        .sort_values(ascending=False)
    )

    account_budget = (
        df.groupby("account_type")["budget_2026"]
        .sum()
        .sort_values(ascending=False)
    )

    status_dist = (
        df.groupby("status")["project_name"]
        .count()
        .sort_values(ascending=False)
    )

    increase_top10 = (
        df.sort_values("change_amount", ascending=False)
        .head(10)[["project_name", "change_amount", "budget_2026", "ministry"]]
        .to_dict(orient="records")
    )

    decrease_top10 = (
        df.sort_values("change_amount", ascending=True)
        .head(10)[["project_name", "change_amount", "budget_2026", "ministry"]]
        .to_dict(orient="records")
    )

    request_vs_final = df[[
        "project_name", "ministry", "request_2026", "budget_2026"
    ]].to_dict(orient="records")

    domain_budget = (
        df.groupby("domain")["budget_2026"]
        .sum()
        .sort_values(ascending=False)
    )

    heatmap = (
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

    charts = {
        "ministry_budget_top10": to_records(ministry_budget),
        "project_type_distribution": to_records(project_type),
        "account_budget": to_records(account_budget),
        "status_distribution": to_records(status_dist),
        "increase_top10": increase_top10,
        "decrease_top10": decrease_top10,
        "request_vs_final": request_vs_final,
        "domain_budget": to_records(domain_budget),
        "domain_ministry_heatmap": heatmap
    }

    with open(OUTPUT_OVERVIEW, "w", encoding="utf-8") as f:
        json.dump(overview, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_CHARTS, "w", encoding="utf-8") as f:
        json.dump(charts, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_RECS, "w", encoding="utf-8") as f:
        json.dump(recommendations, f, ensure_ascii=False, indent=2)

    print("완료:", OUTPUT_OVERVIEW)
    print("완료:", OUTPUT_CHARTS)
    print("완료:", OUTPUT_RECS)
    print("전체 과제 수:", total_projects)
    print("전체 예산:", f"{total_budget:,} 백만원")
    print("참여 부처 수:", total_ministries)

if __name__ == "__main__":
    main()