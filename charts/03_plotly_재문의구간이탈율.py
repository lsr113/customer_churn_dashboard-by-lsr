import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

BINS = ["0회", "1회", "2회 이상"]


def bucket(count):
    if count == 0:
        return "0회"
    if count == 1:
        return "1회"
    return "2회 이상"


def main():
    con = pd.read_csv(os.path.join(DATA_DIR, "data_consultations.csv"), encoding="utf-8-sig")
    cust = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"), encoding="utf-8-sig")

    recontact_counts = (
        con[con["is_recontact"].astype(str).str.strip().str.upper() == "Y"]
        .groupby("customer_id")
        .size()
        .rename("recontact_count")
    )

    merged = cust.merge(recontact_counts, on="customer_id", how="left")
    merged["recontact_count"] = merged["recontact_count"].fillna(0).astype(int)
    merged["구간"] = merged["recontact_count"].apply(bucket)

    overall_rate = (merged["churn_yn"].astype(str).str.strip().str.upper() == "Y").mean() * 100

    summary = (
        merged.groupby("구간")
        .agg(
            고객수=("customer_id", "count"),
            이탈고객수=("churn_yn", lambda s: (s.astype(str).str.strip().str.upper() == "Y").sum()),
        )
        .reindex(BINS)
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100

    colors = {"0회": "#9CA3AF", "1회": "#9CA3AF", "2회 이상": "#DC2626"}

    fig = px.bar(
        summary,
        x="구간",
        y="이탈율",
        color="구간",
        color_discrete_map=colors,
        custom_data=["고객수", "이탈고객수"],
        title="재문의 횟수 구간별 이탈율",
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>"
            "이탈율: %{y:.1f}%"
            "<extra></extra>"
        )
    )

    fig.add_hline(
        y=overall_rate,
        line_dash="dash",
        line_color="#111827",
        annotation_text=f"전체 평균 이탈율 {overall_rate:.1f}%",
        annotation_position="top left",
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="재문의 횟수 구간",
        yaxis_title="이탈율 (%)",
    )

    fig.show()


if __name__ == "__main__":
    main()
