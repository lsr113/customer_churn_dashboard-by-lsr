import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from plotly.subplots import make_subplots

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BQ_DATASET = "7_8_practice"

GRAY = "#9CA3AF"
RED = "#DC2626"


def load_csv(name):
    return pd.read_csv(os.path.join(DATA_DIR, name), encoding="utf-8-sig")


def is_yes(series):
    return series.astype(str).str.strip().str.upper() == "Y"


def churn_stats(df):
    total = len(df)
    churned = is_yes(df["churn_yn"]).sum()
    rate = churned / total * 100 if total > 0 else 0
    return total, churned, rate


def build_voc_chart(voc, cust):
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
        color_discrete_map={"전체 고객": GRAY, "해지관련 부정 VOC 이력 있음": RED},
        custom_data=["고객수", "이탈고객수"],
        title="전체 고객 vs 해지관련 부정 VOC 고객 이탈율 비교",
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y:.1f}%<extra></extra>"
        )
    )
    fig.update_layout(showlegend=False, yaxis_title="이탈율 (%)", xaxis_title=None)
    return fig


def build_channel_csat_chart(sat, con):
    merged = sat.merge(con, on="consult_id", how="inner")

    summary = (
        merged.groupby("channel")
        .agg(
            csat_mean=("csat", "mean"),
            recontact_rate=("is_recontact", lambda s: is_yes(s).mean() * 100),
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
                "<b>%{x}</b><br>CSAT 평균: %{y:.2f}<br>재문의율: %{customdata:.1f}%<extra></extra>"
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
            line=dict(color=RED, width=3),
            marker=dict(size=9),
            hovertemplate=(
                "<b>%{x}</b><br>재문의율: %{y:.1f}%<br>CSAT 평균: %{customdata:.2f}<extra></extra>"
            ),
            customdata=summary["csat_mean"],
        ),
        secondary_y=True,
    )
    fig.update_layout(title="채널별 CSAT 평균 및 재문의율 (CSAT 낮은 순)", hovermode="x unified")
    fig.update_xaxes(title_text="채널")
    fig.update_yaxes(title_text="CSAT 평균", secondary_y=False)
    fig.update_yaxes(title_text="재문의율 (%)", secondary_y=True)
    return fig


def build_recontact_bucket_chart(con, cust):
    bins = ["0회", "1회", "2회 이상"]

    def bucket(count):
        if count == 0:
            return "0회"
        if count == 1:
            return "1회"
        return "2회 이상"

    recontact_counts = (
        con[is_yes(con["is_recontact"])].groupby("customer_id").size().rename("recontact_count")
    )
    merged = cust.merge(recontact_counts, on="customer_id", how="left")
    merged["recontact_count"] = merged["recontact_count"].fillna(0).astype(int)
    merged["구간"] = merged["recontact_count"].apply(bucket)

    overall_rate = is_yes(merged["churn_yn"]).mean() * 100

    summary = (
        merged.groupby("구간")
        .agg(고객수=("customer_id", "count"), 이탈고객수=("churn_yn", lambda s: is_yes(s).sum()))
        .reindex(bins)
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100

    colors = {"0회": GRAY, "1회": GRAY, "2회 이상": RED}

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
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y:.1f}%<extra></extra>"
        )
    )
    fig.add_hline(
        y=overall_rate,
        line_dash="dash",
        line_color="#111827",
        annotation_text=f"전체 평균 이탈율 {overall_rate:.1f}%",
        annotation_position="top left",
    )
    fig.update_layout(showlegend=False, xaxis_title="재문의 횟수 구간", yaxis_title="이탈율 (%)")
    return fig


def build_plan_chart(cust):
    highlight = "베이직"

    summary = (
        cust.groupby("plan")
        .agg(고객수=("customer_id", "count"), 이탈고객수=("churn_yn", lambda s: is_yes(s).sum()))
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100

    colors = {plan: (RED if plan == highlight else GRAY) for plan in summary["plan"]}

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
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y:.1f}%<extra></extra>"
        )
    )
    fig.update_layout(showlegend=False, xaxis_title="요금제", yaxis_title="이탈율 (%)")
    return fig


def build_region_chart(cust):
    highlight = {"부산", "대구"}
    caption_region = "인천"

    summary = (
        cust.groupby("region")
        .agg(고객수=("customer_id", "count"), 이탈고객수=("churn_yn", lambda s: is_yes(s).sum()))
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100

    colors = {region: (RED if region in highlight else GRAY) for region in summary["region"]}

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
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y:.1f}%<extra></extra>"
        )
    )

    caption_row = summary[summary["region"] == caption_region].iloc[0]
    caption_text = (
        f"※ {caption_region}은 표본이 {int(caption_row['고객수'])}건이지만 "
        f"이탈 {int(caption_row['이탈고객수'])}건뿐이라 이탈율 해석에 주의가 필요합니다."
    )

    fig.update_layout(
        showlegend=False, xaxis_title="지역", yaxis_title="이탈율 (%)", margin=dict(b=100)
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
    return fig


def build_tenure_usage_chart(cust, usage):
    cutoff_date = pd.Timestamp("2024-12-31")

    cust = cust.copy()
    cust["join_date"] = pd.to_datetime(cust["join_date"])
    cust["tenure_months"] = (cutoff_date.year - cust["join_date"].dt.year) * 12 + (
        cutoff_date.month - cust["join_date"].dt.month
    )

    avg_usage = usage.groupby("customer_id")["data_gb"].mean().rename("avg_data_gb")
    merged = cust.merge(avg_usage, on="customer_id", how="inner")

    fig = px.scatter(
        merged,
        x="tenure_months",
        y="avg_data_gb",
        color="churn_yn",
        color_discrete_map={"N": GRAY, "Y": RED},
        custom_data=["customer_id", "tenure_months", "avg_data_gb", "churn_yn"],
        title="가입기간 대비 평균 데이터 사용량 (이탈 여부별)",
    )
    fig.update_traces(
        hovertemplate=(
            "고객 ID: %{customdata[0]}<br>가입기간: %{customdata[1]}개월<br>"
            "평균 데이터 사용량: %{customdata[2]:.2f}GB<br>이탈 여부: %{customdata[3]}<extra></extra>"
        )
    )
    fig.update_layout(
        xaxis_title="가입기간 (개월)", yaxis_title="평균 데이터 사용량 (GB)", legend_title_text="이탈 여부"
    )
    return fig


@st.cache_resource
def get_bq_client():
    return bigquery.Client()


@st.cache_data
def load_agents():
    client = get_bq_client()
    return client.query(f"SELECT * FROM `{BQ_DATASET}.agents`").to_dataframe()


@st.cache_data
def load_consult_joined():
    client = get_bq_client()
    query = f"""
        SELECT
            a.agent_id,
            a.team,
            a.overtime_hours_avg,
            a.training_completed_yn,
            s.csat,
            c.is_recontact
        FROM `{BQ_DATASET}.agents` AS a
        JOIN `{BQ_DATASET}.data_consultations` AS c ON a.agent_id = c.agent_id
        JOIN `{BQ_DATASET}.data_satisfaction` AS s ON c.consult_id = s.consult_id
    """
    return client.query(query).to_dataframe()


def classify_nps(score):
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


def enps(df):
    total = len(df)
    if total == 0:
        return 0.0
    groups = df["agent_satisfaction"].apply(classify_nps)
    promoters = (groups == "promoter").sum()
    detractors = (groups == "detractor").sum()
    return (promoters - detractors) / total * 100


def build_enps_gauge(agents_df, team_filter):
    df = agents_df if team_filter is None else agents_df[agents_df["team"] == team_filter]
    value = enps(df)
    title = f"{team_filter} eNPS" if team_filter else "전체 eNPS"
    bar_color = RED if value < 0 else "#111827"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"valueformat": ".1f"},
            title={"text": title},
            gauge={
                "axis": {"range": [-100, 100]},
                "bar": {"color": bar_color},
                "steps": [
                    {"range": [-100, 0], "color": "#FEE2E2"},
                    {"range": [0, 100], "color": "#E5E7EB"},
                ],
                "threshold": {"line": {"color": "#111827", "width": 2}, "thickness": 0.8, "value": 0},
            },
        )
    )
    fig.update_layout(height=320, margin=dict(t=60, b=20, l=40, r=40))
    return fig


def agent_csat_summary(df):
    summary = (
        df.groupby("agent_id")
        .agg(overtime_hours_avg=("overtime_hours_avg", "first"), avg_csat=("csat", "mean"))
        .reset_index()
    )
    summary["overtime_hours_avg"] = summary["overtime_hours_avg"].astype(float)
    summary["avg_csat"] = summary["avg_csat"].astype(float)
    return summary


def build_burnout_csat_chart(consult_df, team_filter):
    df = consult_df if team_filter is None else consult_df[consult_df["team"] == team_filter]
    agent_summary = agent_csat_summary(df)

    correlation = agent_summary["overtime_hours_avg"].corr(agent_summary["avg_csat"])

    fig = px.scatter(
        agent_summary,
        x="overtime_hours_avg",
        y="avg_csat",
        trendline="ols",
        custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
        title=f"초과근무 시간과 CSAT 평균의 관계 ({team_filter if team_filter else '전체'})",
    )
    fig.update_traces(
        hovertemplate=(
            "상담원 ID: %{customdata[0]}<br>초과근무 시간: %{customdata[1]}시간<br>"
            "CSAT 평균: %{customdata[2]:.2f}<extra></extra>"
        ),
        selector=dict(mode="markers"),
    )
    fig.add_annotation(
        text=f"r = {correlation:.2f}" if pd.notna(correlation) else "r = N/A",
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.98,
        showarrow=False,
        font=dict(size=16, color="#111827"),
    )
    fig.update_layout(xaxis_title="초과근무 시간 (평균, 시간)", yaxis_title="CSAT 평균")
    return fig


OUTLIER_AGENTS = ["AG02", "AG03"]


def build_outlier_comparison_chart(consult_df, team_filter):
    df = consult_df if team_filter is None else consult_df[consult_df["team"] == team_filter]

    summary_all = agent_csat_summary(df)
    summary_excl = summary_all[~summary_all["agent_id"].isin(OUTLIER_AGENTS)]

    def panel(summary):
        n = len(summary)
        trendline = "ols" if n >= 2 else None
        correlation = summary["overtime_hours_avg"].corr(summary["avg_csat"]) if n >= 2 else float("nan")

        fig = px.scatter(
            summary,
            x="overtime_hours_avg",
            y="avg_csat",
            trendline=trendline,
            custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
        )
        fig.update_traces(
            hovertemplate=(
                "상담원 ID: %{customdata[0]}<br>초과근무 시간: %{customdata[1]}시간<br>"
                "CSAT 평균: %{customdata[2]:.2f}<extra></extra>"
            ),
            selector=dict(mode="markers"),
        )

        slope = float("nan")
        if trendline:
            trendline_results = px.get_trendline_results(fig)
            if not trendline_results.empty:
                slope = trendline_results["px_fit_results"].iloc[0].params[1]

        return fig, correlation, slope, n

    fig_all, corr_all, slope_all, n_all = panel(summary_all)
    fig_excl, corr_excl, slope_excl, n_excl = panel(summary_excl)

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

    def annotation_text(correlation, slope):
        r_text = f"{correlation:.2f}" if pd.notna(correlation) else "N/A"
        slope_text = f"{slope:.3f}" if pd.notna(slope) else "N/A"
        return f"r = {r_text}<br>기울기 = {slope_text}"

    fig.add_annotation(
        text=annotation_text(corr_all, slope_all),
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
        text=annotation_text(corr_excl, slope_excl),
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
        title=f"이상치(AG02·AG03) 포함/제외 비교 ({team_filter if team_filter else '전체'})",
        showlegend=False,
    )
    return fig


def main():
    st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide")
    st.title("고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드")
    st.caption("제작: 이성령")

    cust = load_csv("data_customers.csv")
    voc = load_csv("data_voc.csv")
    sat = load_csv("data_satisfaction.csv")
    con = load_csv("data_consultations.csv")
    usage = load_csv("data_usage_history.csv")

    total, churned, rate = churn_stats(cust)

    col1, col2, col3 = st.columns(3)
    col1.metric("전체 고객 수", f"{total}명")
    col2.metric("이탈 고객 수", f"{churned}명")
    col3.metric("전체 이탈율", f"{rate:.1f}%")

    st.subheader("① VOC로 본 이탈")
    st.plotly_chart(build_voc_chart(voc, cust), use_container_width=True)

    st.subheader("② 채널·만족도로 본 이탈")
    st.plotly_chart(build_channel_csat_chart(sat, con), use_container_width=True)

    st.subheader("③ 재문의 반복으로 본 이탈")
    st.plotly_chart(build_recontact_bucket_chart(con, cust), use_container_width=True)

    st.subheader("④ 요금제로 본 이탈")
    st.plotly_chart(build_plan_chart(cust), use_container_width=True)

    st.subheader("⑤ 지역으로 본 이탈")
    st.plotly_chart(build_region_chart(cust), use_container_width=True)

    st.subheader("⑥ 가입기간·이용량으로 본 이탈")
    st.plotly_chart(build_tenure_usage_chart(cust, usage), use_container_width=True)

    st.divider()
    st.subheader("상담원 관점: 직원만족도와 고객 경험")

    try:
        agents_df = load_agents()
        consult_df = load_consult_joined()
    except Exception:
        st.info(
            "이 섹션은 BigQuery 연동이 필요합니다. 배포 환경에는 인증 정보가 설정되어 있지 않아 "
            "표시되지 않으며, gcloud 인증이 되어 있는 로컬 환경에서만 확인할 수 있습니다."
        )
    else:
        teams = sorted(agents_df["team"].unique())
        selected_team = st.selectbox("팀 선택", ["전체"] + teams)
        team_filter = None if selected_team == "전체" else selected_team

        st.plotly_chart(build_enps_gauge(agents_df, team_filter), use_container_width=True)
        st.plotly_chart(build_burnout_csat_chart(consult_df, team_filter), use_container_width=True)
        st.plotly_chart(build_outlier_comparison_chart(consult_df, team_filter), use_container_width=True)


if __name__ == "__main__":
    main()
