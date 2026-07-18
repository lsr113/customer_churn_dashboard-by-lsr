import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

HIGHLIGHT = {"부산", "대구"}
CAPTION_REGION = "인천"


def main():
    cust = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"), encoding="utf-8-sig")

    summary = (
        cust.groupby("region")
        .agg(
            고객수=("customer_id", "count"),
            이탈고객수=("churn_yn", lambda s: (s.astype(str).str.strip().str.upper() == "Y").sum()),
        )
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100

    colors = {region: ("#DC2626" if region in HIGHLIGHT else "#9CA3AF") for region in summary["region"]}

    fig = px.bar(
        summary,
        x="region",
        y="이탈율",
        color="region",
        color_discrete_map=colors,
        custom_data=["고객수", "이탈고객수"],
        title="지역별 이탈율",
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

    caption_row = summary[summary["region"] == CAPTION_REGION].iloc[0]
    caption_text = (
        f"※ {CAPTION_REGION}은 표본이 {int(caption_row['고객수'])}건이지만 "
        f"이탈 {int(caption_row['이탈고객수'])}건뿐이라 이탈율 해석에 주의가 필요합니다."
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="지역",
        yaxis_title="이탈율 (%)",
        margin=dict(b=100),
    )
    fig.add_annotation(
        text=caption_text,
        xref="paper",
        yref="paper",
        x=0,
        y=-0.28,
        showarrow=False,
        align="left",
        font=dict(size=12, color="#6B7280"),
    )

    fig.show()


if __name__ == "__main__":
    main()
