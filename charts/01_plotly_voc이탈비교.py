import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def churn_stats(df):
    total = len(df)
    churned = (df["churn_yn"].astype(str).str.strip().str.upper() == "Y").sum()
    rate = churned / total * 100 if total > 0 else 0
    return total, churned, rate


def main():
    voc = pd.read_csv(os.path.join(DATA_DIR, "data_voc.csv"), encoding="utf-8-sig")
    cust = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"), encoding="utf-8-sig")

    target_voc = voc[
        (voc["category"].astype(str).str.strip() == "해지관련")
        & (voc["sentiment"].astype(str).str.strip() == "부정")
    ]
    target_customer_ids = target_voc["customer_id"].dropna().unique()
    target_cust = cust[cust["customer_id"].isin(target_customer_ids)]

    all_total, all_churned, all_rate = churn_stats(cust)
    tgt_total, tgt_churned, tgt_rate = churn_stats(target_cust)

    plot_df = pd.DataFrame(
        {
            "구분": ["전체 고객", "해지관련 부정 VOC 이력 있음"],
            "이탈율": [all_rate, tgt_rate],
            "고객수": [all_total, tgt_total],
            "이탈고객수": [all_churned, tgt_churned],
        }
    )

    fig = px.bar(
        plot_df,
        x="구분",
        y="이탈율",
        color="구분",
        color_discrete_map={
            "전체 고객": "#9CA3AF",
            "해지관련 부정 VOC 이력 있음": "#DC2626",
        },
        custom_data=["고객수", "이탈고객수"],
        title="전체 고객 vs 해지관련 부정 VOC 고객 이탈율 비교",
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
        yaxis_title="이탈율 (%)",
        xaxis_title=None,
    )

    fig.show()


if __name__ == "__main__":
    main()
