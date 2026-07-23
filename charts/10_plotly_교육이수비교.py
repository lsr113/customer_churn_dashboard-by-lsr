import plotly.graph_objects as go
from google.cloud import bigquery
from plotly.subplots import make_subplots

DATASET = "7_8_practice"

RED = "#DC2626"
GRAY = "#9CA3AF"


def fetch_data():
    client = bigquery.Client()
    query = f"""
        SELECT
            a.training_completed_yn,
            AVG(s.csat) AS avg_csat,
            AVG(CAST(c.is_recontact AS INT64)) * 100 AS recontact_rate,
            COUNT(*) AS n
        FROM `{DATASET}.agents` AS a
        JOIN `{DATASET}.data_consultations` AS c ON a.agent_id = c.agent_id
        JOIN `{DATASET}.data_satisfaction` AS s ON c.consult_id = s.consult_id
        GROUP BY a.training_completed_yn
    """
    return client.query(query).to_dataframe()


def main():
    df = fetch_data()
    df["label"] = df["training_completed_yn"].map({True: "이수(Y)", False: "미이수(N)"})
    df = df.sort_values("training_completed_yn", ascending=False)

    colors = df["training_completed_yn"].map({True: RED, False: GRAY})

    fig = make_subplots(rows=1, cols=2, subplot_titles=["CSAT 평균", "재문의율 (%)"])

    fig.add_trace(
        go.Bar(
            x=df["label"],
            y=df["avg_csat"],
            marker_color=colors,
            text=df["avg_csat"].round(2),
            texttemplate="%{text}",
            textposition="outside",
            customdata=df["n"],
            hovertemplate="%{x}<br>CSAT 평균: %{y:.2f}<br>표본 수: %{customdata}건<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=df["label"],
            y=df["recontact_rate"],
            marker_color=colors,
            text=df["recontact_rate"].round(1).astype(str) + "%",
            texttemplate="%{text}",
            textposition="outside",
            customdata=df["n"],
            hovertemplate="%{x}<br>재문의율: %{y:.1f}%<br>표본 수: %{customdata}건<extra></extra>",
        ),
        row=1,
        col=2,
    )

    fig.update_yaxes(title_text="CSAT 평균", range=[0, df["avg_csat"].max() * 1.3], row=1, col=1)
    fig.update_yaxes(title_text="재문의율 (%)", range=[0, df["recontact_rate"].max() * 1.3], row=1, col=2)

    fig.update_layout(
        title="교육 이수 여부에 따른 CSAT 평균 및 재문의율 비교",
        showlegend=False,
    )

    fig.show()

    print(df[["label", "avg_csat", "recontact_rate", "n"]].to_string(index=False))


if __name__ == "__main__":
    main()
