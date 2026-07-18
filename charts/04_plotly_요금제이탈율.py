import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

HIGHLIGHT = "베이직"


def main():
    cust = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"), encoding="utf-8-sig")

    summary = (
        cust.groupby("plan")
        .agg(
            고객수=("customer_id", "count"),
            이탈고객수=("churn_yn", lambda s: (s.astype(str).str.strip().str.upper() == "Y").sum()),
        )
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100

    colors = {plan: ("#DC2626" if plan == HIGHLIGHT else "#9CA3AF") for plan in summary["plan"]}

    fig = px.bar(
        summary,
        x="plan",
        y="이탈율",
        color="plan",
        color_discrete_map=colors,
        custom_data=["고객수", "이탈고객수"],
        title="요금제별 이탈율",
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

    fig.update_layout(
        showlegend=False,
        xaxis_title="요금제",
        yaxis_title="이탈율 (%)",
    )

    fig.show()


if __name__ == "__main__":
    main()
