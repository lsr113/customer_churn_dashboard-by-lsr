import os

import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "01_matplotlib_voc이탈비교.png")

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def churn_rate(df):
    total = len(df)
    churned = (df["churn_yn"].astype(str).str.strip().str.upper() == "Y").sum()
    return churned / total * 100 if total > 0 else 0


def main():
    voc = pd.read_csv(os.path.join(DATA_DIR, "data_voc.csv"), encoding="utf-8-sig")
    cust = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"), encoding="utf-8-sig")

    target_voc = voc[
        (voc["category"].astype(str).str.strip() == "해지관련")
        & (voc["sentiment"].astype(str).str.strip() == "부정")
    ]
    target_customer_ids = target_voc["customer_id"].dropna().unique()
    target_cust = cust[cust["customer_id"].isin(target_customer_ids)]

    all_rate = churn_rate(cust)
    target_rate = churn_rate(target_cust)

    labels = ["전체 고객", "해지관련 부정 VOC 이력 있음"]
    rates = [all_rate, target_rate]
    colors = ["#9CA3AF", "#DC2626"]

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, rates, color=colors, width=0.5)

    for bar, rate in zip(bars, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
        )

    ax.set_ylabel("이탈율 (%)")
    ax.set_title("전체 고객 vs 해지관련 부정 VOC 고객 이탈율 비교")
    ax.set_ylim(0, max(rates) * 1.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    print(f"SAVED={OUTPUT_PATH}")
    print(f"ALL_RATE={all_rate:.2f}")
    print(f"TARGET_RATE={target_rate:.2f}")


if __name__ == "__main__":
    main()
