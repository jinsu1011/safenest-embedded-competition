# -*- coding: utf-8 -*-
"""1페이지 재해 통계 도넛. 슬라이드 배치 비율(3.05 x 2.62 in)에 맞춰 생성한다."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "..", "previews")

for cand in ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic"]:
    try:
        font_manager.findfont(cand, fallback_to_default=False)
        plt.rcParams["font.family"] = cand
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

NAVY, RED, GREY = "#1B2A41", "#C0392B", "#6B7280"
DEAD, OTHER = 136, 202          # 고용노동부 밀폐공간 질식재해 예방 보도자료(2024)

# 슬라이드 배치 비율 3.05 : 2.62 를 그대로 유지한다. bbox_inches 를 쓰지 않아야
# 그림 비율이 보존되고, 배치 시 가로로 늘어나는 왜곡이 생기지 않는다.
SCALE = 1.35
fig = plt.figure(figsize=(3.05 * SCALE, 2.62 * SCALE), dpi=230)
fig.patch.set_facecolor("white")

ax = fig.add_axes([0.09, 0.125, 0.82, 0.855])
wedges, _ = ax.pie([DEAD, OTHER], startangle=90, counterclock=False,
                   colors=[RED, "#C9D2DC"],
                   wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
ax.set_aspect("equal")
ax.text(0, 0.22, "재해자 338명 중", ha="center", va="center", fontsize=11, color=GREY)
ax.text(0, -0.16, "136명", ha="center", va="center", fontsize=23, color=RED, fontweight="bold")
ax.text(0, -0.50, "사망", ha="center", va="center", fontsize=13.5, color=RED)

fig.legend(wedges, ["사망 136명", "그 외 재해자 202명"],
           loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=2,
           frameon=False, fontsize=10.5, handlelength=1.0, handleheight=0.9,
           columnspacing=1.4, labelcolor=NAVY)

fig.savefig(os.path.join(OUT, "chart_victims.png"), facecolor="white")
plt.close(fig)
print("chart_victims.png 재생성")
