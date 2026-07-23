import plotly.express as px
from google.cloud import bigquery

DATASET = "7_8_practice"


def main():
    client = bigquery.Client()

    query = f"""
        SELECT
            a.agent_id,
            a.overtime_hours_avg,
            AVG(s.csat) AS avg_csat
        FROM `{DATASET}.agents` AS a
        JOIN `{DATASET}.data_consultations` AS c ON a.agent_id = c.agent_id
        JOIN `{DATASET}.data_satisfaction` AS s ON c.consult_id = s.consult_id
        GROUP BY a.agent_id, a.overtime_hours_avg
    """
    df = client.query(query).to_dataframe()

    correlation = df["overtime_hours_avg"].corr(df["avg_csat"])

    fig = px.scatter(
        df,
        x="overtime_hours_avg",
        y="avg_csat",
        trendline="ols",
        custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
        title="초과근무 시간과 상담원별 CSAT 평균의 관계",
    )

    fig.update_traces(
        hovertemplate=(
            "상담원 ID: %{customdata[0]}<br>"
            "초과근무 시간: %{customdata[1]}시간<br>"
            "CSAT 평균: %{customdata[2]:.2f}"
            "<extra></extra>"
        ),
        selector=dict(mode="markers"),
    )

    fig.add_annotation(
        text=f"r = {correlation:.2f}",
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.98,
        showarrow=False,
        align="right",
        font=dict(size=16, color="#111827"),
    )

    fig.update_layout(
        xaxis_title="초과근무 시간 (평균, 시간)",
        yaxis_title="CSAT 평균",
    )

    fig.show()

    print(f"CORRELATION={correlation:.4f}")


if __name__ == "__main__":
    main()
