"""Stage 7 (Interact): a self-contained interactive HTML explorer built with Plotly.

Open outputs/interactive/explorer.html in any browser (needs internet only to load plotly.js from a CDN).
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import CATEGORICAL, MONTH_ORDER, OUT, SEED
from .eda import rate_table

C_NO, C_YES, C_ACC = "#4C72B0", "#DD8452", "#2E8B57"


def _rate_fig(cdf):
    cdf = cdf.copy()
    fig = go.Figure()
    for i, c in enumerate(CATEGORICAL):
        t = rate_table(cdf, c, order=MONTH_ORDER if c == "month" else None)
        if c != "month":
            t = t.sort_values("rate", ascending=False)
        fig.add_bar(x=t.index.astype(str), y=t["rate"] * 100, visible=(i == 0), marker_color=C_ACC, name=c,
                    error_y=dict(type="data", symmetric=False, array=(t["ci_high"] - t["rate"]) * 100,
                                 arrayminus=(t["rate"] - t["ci_low"]) * 100),
                    customdata=np.c_[t["n"], t["subscribed"]],
                    hovertemplate="<b>%{x}</b><br>rate %{y:.1f}%<br>n = %{customdata[0]:,}<br>subscribed = %{customdata[1]:,}<extra></extra>")
    buttons = [dict(label=c, method="update", args=[{"visible": [j == i for j in range(len(CATEGORICAL))]},
                                                      {"title": f"Subscription rate by {c} (95% exact CI)"}])
               for i, c in enumerate(CATEGORICAL)]
    fig.add_hline(y=cdf["y_bin"].mean() * 100, line_dash="dash", line_color=C_YES,
                  annotation_text=f"overall {cdf['y_bin'].mean() * 100:.1f}%")
    fig.update_layout(title=f"Subscription rate by {CATEGORICAL[0]} (95% exact CI)", yaxis_title="Subscription rate (%)",
                      updatemenus=[dict(buttons=buttons, x=0.0, y=1.18, xanchor="left")], template="plotly_white", height=470)
    return fig


def _hist_fig(cdf):
    specs = [("age", "age (years)"), ("balance", "balance (EUR, clipped at 1st-99th pct)"),
             ("duration", "duration (s, clipped at 99th pct)"), ("campaign", "campaign contacts (clipped at 99th pct)"),
             ("previous", "previous contacts (clipped at 99th pct)"), ("day", "day of month")]
    fig = go.Figure()
    for i, (c, lab) in enumerate(specs):
        s = cdf[c]
        lo, hi = (s.quantile(.01), s.quantile(.99)) if c in ("balance",) else (s.min(), s.quantile(.99) if c in ("duration", "campaign", "previous") else s.max())
        for yv, col, nm in (("no", C_NO, "No"), ("yes", C_YES, "Yes")):
            v = cdf.loc[(cdf["y"] == yv) & (s >= lo) & (s <= hi), c]
            fig.add_histogram(x=v, histnorm="probability density", opacity=.6, marker_color=col, name=nm,
                              visible=(i == 0), legendgroup=nm, showlegend=(i == 0), nbinsx=50)
    buttons = [dict(label=c, method="update", args=[{"visible": [(j // 2) == i for j in range(2 * len(specs))],
                                                      "showlegend": [(j // 2) == i for j in range(2 * len(specs))]},
                                                     {"title": f"Distribution of {lab} by outcome", "xaxis": {"title": lab}}])
               for i, (c, lab) in enumerate(specs)]
    fig.update_layout(barmode="overlay", title=f"Distribution of {specs[0][1]} by outcome", xaxis_title=specs[0][1],
                      yaxis_title="Density", updatemenus=[dict(buttons=buttons, x=0.0, y=1.18, xanchor="left")],
                      template="plotly_white", height=470)
    return fig


def _scatter_fig(cdf, n=3000):
    s = cdf.sample(n, random_state=SEED)
    fig = go.Figure()
    for yv, col, nm in (("no", C_NO, "No"), ("yes", C_YES, "Yes")):
        d = s[s["y"] == yv]
        fig.add_scattergl(x=d["age"], y=d["duration"], mode="markers", marker=dict(color=col, size=6, opacity=.55), name=nm,
                          customdata=np.c_[d["job"], d["month"], d["balance"], d["campaign"], d["poutcome"]],
                          hovertemplate=("age %{x}, call %{y} s<br>job: %{customdata[0]}<br>month: %{customdata[1]}"
                                         "<br>balance: EUR %{customdata[2]:,}<br>contacts: %{customdata[3]}<br>previous outcome: %{customdata[4]}<extra>" + nm + "</extra>"))
    fig.update_layout(title=f"Age vs. call duration (random sample of {n:,} clients; hover for details, drag to zoom)",
                      xaxis_title="Age (years)", yaxis_title="Call duration (s, log scale)", yaxis_type="log", template="plotly_white", height=470)
    fig.update_yaxes(rangemode="tozero") if False else None
    return fig


def build_explorer(cdf: pd.DataFrame, path=None):
    path = path or OUT / "interactive" / "explorer.html"
    parts = [_rate_fig(cdf), _hist_fig(cdf), _scatter_fig(cdf[cdf["duration"] > 0])]
    html = ["<html><head><meta charset='utf-8'><title>Bank Marketing - interactive explorer</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1000px;margin:24px auto;padding:0 12px}</style></head><body>",
            "<h2>Bank Marketing (UCI #222) - interactive explorer</h2>",
            "<p>Stage 7 of the seven-stage visualization framework (Interact). Use the dropdowns, hover for exact values, "
            "drag to zoom and double-click to reset. Source: Moro, Cortez &amp; Rita (2014), UCI Machine Learning Repository.</p>"]
    for i, f in enumerate(parts):
        html.append(f.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))
    html.append("</body></html>")
    path.write_text("\n".join(html), encoding="utf-8")
    return path
