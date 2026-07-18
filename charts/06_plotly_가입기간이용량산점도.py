import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

CUTOFF_DATE = pd.Timestamp("2024-12-31")


def main():
    cust = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"), encoding="utf-8-sig")
    usage = pd.read_csv(os.path.join(DATA_DIR, "data_usage_history.csv"), encoding="utf-8-sig")

    cust["join_date"] = pd.to_datetime(cust["join_date"])
    cust["tenure_months"] = (
        (CUTOFF_DATE.year - cust["join_date"].dt.year) * 12
        + (CUTOFF_DATE.month - cust["join_date"].dt.month)
    )

    avg_usage = usage.groupby("customer_id")["data_gb"].mean().rename("avg_data_gb")

    merged = cust.merge(avg_usage, on="customer_id", how="inner")

    fig = px.scatter(
        merged,
        x="tenure_months",
        y="avg_data_gb",
        color="churn_yn",
        color_discrete_map={"N": "#9CA3AF", "Y": "#DC2626"},
        custom_data=["customer_id", "tenure_months", "avg_data_gb", "churn_yn"],
        title="가입기간 대비 평균 데이터 사용량 (이탈 여부별)",
    )

    fig.update_traces(
        hovertemplate=(
            "고객 ID: %{customdata[0]}<br>"
            "가입기간: %{customdata[1]}개월<br>"
            "평균 데이터 사용량: %{customdata[2]:.2f}GB<br>"
            "이탈 여부: %{customdata[3]}"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        xaxis_title="가입기간 (개월)",
        yaxis_title="평균 데이터 사용량 (GB)",
        legend_title_text="이탈 여부",
    )

    fig.show()


if __name__ == "__main__":
    main()
