import plotly.graph_objects as go
from google.cloud import bigquery

TABLE = "7_8_practice.agents"

RED = "#DC2626"
DARK = "#111827"
NEGATIVE_BG = "#FEE2E2"
POSITIVE_BG = "#E5E7EB"


def classify(score):
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


def enps(df):
    total = len(df)
    if total == 0:
        return 0.0
    groups = df["agent_satisfaction"].apply(classify)
    promoters = (groups == "promoter").sum()
    detractors = (groups == "detractor").sum()
    return (promoters - detractors) / total * 100


def build_gauge(fig, value, domain, title):
    bar_color = RED if value < 0 else DARK
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "", "valueformat": ".1f"},
            title={"text": title},
            gauge={
                "axis": {"range": [-100, 100]},
                "bar": {"color": bar_color},
                "steps": [
                    {"range": [-100, 0], "color": NEGATIVE_BG},
                    {"range": [0, 100], "color": POSITIVE_BG},
                ],
                "threshold": {
                    "line": {"color": DARK, "width": 2},
                    "thickness": 0.8,
                    "value": 0,
                },
            },
            domain=domain,
        )
    )


def build_number_card(fig, value, domain, title):
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=value,
            number={"suffix": "", "valueformat": ".1f", "font": {"color": RED if value < 0 else DARK}},
            title={"text": title},
            domain=domain,
        )
    )


def main():
    client = bigquery.Client()
    df = client.query(f"SELECT * FROM `{TABLE}`").to_dataframe()

    overall_enps = enps(df)

    team_enps = {
        team: enps(sub_df) for team, sub_df in df.groupby("team")
    }
    team_order = sorted(team_enps.keys())

    fig = go.Figure()

    build_gauge(fig, overall_enps, {"x": [0, 0.55], "y": [0, 1]}, "전체 eNPS")

    card_x_ranges = [(0.60, 0.75), (0.76, 0.91), (0.92, 1.0)]
    for team, (x0, x1) in zip(team_order, card_x_ranges):
        build_number_card(fig, team_enps[team], {"x": [x0, x1], "y": [0.35, 0.75]}, f"{team} eNPS")

    fig.update_layout(
        title="직원만족도 eNPS 스코어카드",
        height=420,
        margin=dict(t=80, b=20, l=20, r=20),
    )

    fig.show()

    print(f"전체 eNPS: {overall_enps:.1f}")
    for team in team_order:
        print(f"{team} eNPS: {team_enps[team]:.1f}")


if __name__ == "__main__":
    main()
