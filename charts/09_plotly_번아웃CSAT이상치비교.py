import plotly.express as px
from google.cloud import bigquery
from plotly.subplots import make_subplots

DATASET = "7_8_practice"
OUTLIER_AGENTS = ["AG02", "AG03"]


def fetch_data():
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
    return client.query(query).to_dataframe()


def build_panel(df, label):
    correlation = df["overtime_hours_avg"].corr(df["avg_csat"])

    fig = px.scatter(
        df,
        x="overtime_hours_avg",
        y="avg_csat",
        trendline="ols",
        custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
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

    trendline_results = px.get_trendline_results(fig)
    slope = trendline_results["px_fit_results"].iloc[0].params[1]

    return fig, correlation, slope, len(df)


def main():
    df_all = fetch_data()
    df_excl = df_all[~df_all["agent_id"].isin(OUTLIER_AGENTS)]

    fig_all, corr_all, slope_all, n_all = build_panel(df_all, "포함")
    fig_excl, corr_excl, slope_excl, n_excl = build_panel(df_excl, "제외")

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=[
            f"AG02·AG03 포함 (n={n_all})",
            f"AG02·AG03 제외 (n={n_excl})",
        ],
    )

    for trace in fig_all.data:
        fig.add_trace(trace, row=1, col=1)
    for trace in fig_excl.data:
        fig.add_trace(trace, row=1, col=2)

    fig.add_annotation(
        text=f"r = {corr_all:.2f}<br>기울기 = {slope_all:.3f}",
        xref="x domain",
        yref="y domain",
        x=0.98,
        y=0.98,
        showarrow=False,
        align="right",
        font=dict(size=14, color="#111827"),
        row=1,
        col=1,
    )
    fig.add_annotation(
        text=f"r = {corr_excl:.2f}<br>기울기 = {slope_excl:.3f}",
        xref="x domain",
        yref="y domain",
        x=0.98,
        y=0.98,
        showarrow=False,
        align="right",
        font=dict(size=14, color="#111827"),
        row=1,
        col=2,
    )

    fig.update_xaxes(title_text="초과근무 시간 (평균, 시간)", row=1, col=1)
    fig.update_xaxes(title_text="초과근무 시간 (평균, 시간)", row=1, col=2)
    fig.update_yaxes(title_text="CSAT 평균", row=1, col=1)

    fig.update_layout(
        title="이상치(AG02·AG03) 포함/제외 비교 — 초과근무 시간과 CSAT 평균",
        showlegend=False,
    )

    fig.show()

    print(f"[포함, n={n_all}] r = {corr_all:.4f}, 기울기 = {slope_all:.4f}")
    print(f"[제외, n={n_excl}] r = {corr_excl:.4f}, 기울기 = {slope_excl:.4f}")


if __name__ == "__main__":
    main()
