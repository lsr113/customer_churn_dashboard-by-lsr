import os

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    sat = pd.read_csv(os.path.join(DATA_DIR, "data_satisfaction.csv"), encoding="utf-8-sig")
    con = pd.read_csv(os.path.join(DATA_DIR, "data_consultations.csv"), encoding="utf-8-sig")

    merged = sat.merge(con, on="consult_id", how="inner")

    summary = (
        merged.groupby("channel")
        .agg(
            csat_mean=("csat", "mean"),
            recontact_rate=("is_recontact", lambda s: (s.astype(str).str.strip().str.upper() == "Y").mean() * 100),
        )
        .reset_index()
        .sort_values("csat_mean", ascending=True)
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=summary["channel"],
            y=summary["csat_mean"],
            name="CSAT 평균",
            marker_color="#6B7280",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CSAT 평균: %{y:.2f}<br>"
                "재문의율: %{customdata:.1f}%"
                "<extra></extra>"
            ),
            customdata=summary["recontact_rate"],
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=summary["channel"],
            y=summary["recontact_rate"],
            name="재문의율",
            mode="lines+markers",
            line=dict(color="#DC2626", width=3),
            marker=dict(size=9),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "재문의율: %{y:.1f}%<br>"
                "CSAT 평균: %{customdata:.2f}"
                "<extra></extra>"
            ),
            customdata=summary["csat_mean"],
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="채널별 CSAT 평균 및 재문의율 (CSAT 낮은 순)",
        hovermode="x unified",
    )
    fig.update_xaxes(title_text="채널")
    fig.update_yaxes(title_text="CSAT 평균", secondary_y=False)
    fig.update_yaxes(title_text="재문의율 (%)", secondary_y=True)

    fig.show()


if __name__ == "__main__":
    main()
