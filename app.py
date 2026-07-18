import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

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


if __name__ == "__main__":
    main()
