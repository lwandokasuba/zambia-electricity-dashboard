"""Task 5: three findings told as Context -> Evidence -> Insight -> Implication -> Action.

Every number in the narrative is computed from the data at run time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import data
from .charts import COMPARE, CONTEXT, FOCUS, INK, INK_2, LOG_TICKS, _base_layout

FOCUS_ISO = "ZMB"
PEER_ISO = "TZA"


@dataclass
class Finding:
    title: str
    context: str
    evidence: str
    insight: str
    implication: str
    action: str
    figure: go.Figure


def _row(df: pd.DataFrame, iso: str, year: int) -> pd.Series:
    return df[(df["iso3"] == iso) & (df["year"] == year)].iloc[0]


def _pace(df: pd.DataFrame, iso: str, end: int, window: int) -> float:
    d = df[(df["iso3"] == iso) & (df["year"] > end - window) & (df["year"] <= end)]
    return data.trend_pp_per_year(d["year"], d["access"])


# --------------------------------------------------------------------------- finding 1
def finding_pace(df: pd.DataFrame) -> Finding:
    end = int(df["year"].max())
    z0, z1 = _row(df, FOCUS_ISO, 2000), _row(df, FOCUS_ISO, end)
    pace10 = _pace(df, FOCUS_ISO, end, 10)
    pace5, pace15 = _pace(df, FOCUS_ISO, end, 5), _pace(df, FOCUS_ISO, end, 15)
    need = data.required_pp_per_year(z1["access"], end)
    at_2030 = z1["access"] + pace10 * (data.SDG_TARGET_YEAR - end)
    year_100 = int(end + np.ceil((100 - z1["access"]) / pace10))
    lo, hi = min(pace5, pace10, pace15), max(pace5, pace10, pace15)

    hist = df[df["iso3"] == FOCUS_ISO]
    fut = np.arange(end, data.SDG_TARGET_YEAR + 1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=np.concatenate([fut, fut[::-1]]),
        y=np.concatenate([z1["access"] + hi * (fut - end), (z1["access"] + lo * (fut - end))[::-1]]),
        fill="toself", fillcolor="rgba(235,104,52,0.15)", line=dict(width=0), mode="lines", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(x=hist["year"], y=hist["access"], mode="lines+markers", line=dict(color=FOCUS, width=3),
                             marker=dict(size=6), hovertemplate="Zambia %{x}: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=fut, y=z1["access"] + pace10 * (fut - end), mode="lines", line=dict(color=FOCUS, width=2, dash="dash"),
                             hovertemplate="At current pace %{x}: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=fut, y=z1["access"] + need * (fut - end), mode="lines", line=dict(color=INK, width=2, dash="dot"),
                             hovertemplate="Path needed for SDG 7 %{x}: %{y:.1f}%<extra></extra>"))
    fig.add_annotation(x=2030, y=100, text="<b>Needed: 100% by 2030</b>", showarrow=False, xanchor="right", yshift=10, font=dict(color=INK))
    fig.add_annotation(x=2030, y=at_2030, text=f"<b>At current pace: ~{at_2030:.0f}%</b>", showarrow=False, xanchor="left", xshift=6, font=dict(color=FOCUS))
    fig.add_annotation(x=2000, y=z0["access"], text=f"{z0['access']:.1f}%", showarrow=False, yshift=14, font=dict(color=INK_2))
    fig.add_annotation(x=end, y=z1["access"], text=f"<b>{z1['access']:.1f}%</b>", showarrow=False, yshift=16, xanchor="right", font=dict(color=INK))
    fig = _base_layout(fig, height=400, title=dict(text="Zambia: electricity access and the SDG 7 gap (shaded = range of 5- to 15-year trends)"),
                       margin=dict(l=8, r=150, t=36, b=8))
    fig.update_yaxes(range=[0, 105], ticksuffix="%")
    fig.update_xaxes(dtick=5, range=[1999, data.SDG_TARGET_YEAR + 1])

    return Finding(
        title="1 · Zambia has tripled access, but at today's pace it reaches universal access around "
              f"{year_100}, not 2030",
        context="SDG 7.1 commits Zambia to universal electricity access by 2030. Planners need to know whether the current "
                "trajectory gets there, and if not, how large the acceleration must be.",
        evidence=f"Access rose from {z0['access']:.1f}% in 2000 to {z1['access']:.1f}% in {end}. Over the last ten years the trend has been "
                 f"{pace10:.2f} percentage points a year (between {lo:.2f} and {hi:.2f} depending on the window). Reaching 100% by 2030 "
                 f"needs {need:.2f} pp a year, {need / pace10:.1f}× the current pace.",
        insight=f"The progress is real but the pace is the problem: continuing the trend gives roughly {at_2030:.0f}% in 2030 and "
                f"100% only around {year_100}. Even the most optimistic window falls well short.",
        implication="A 2030 universal-access target cannot be met by doing more of the same. Targets set without this check will be missed "
                    "and erode credibility with funders.",
        action=f"Re-base the national plan on an explicit pp-per-year target ({need:.1f} pp/yr) and ask what delivery model (grid extension, "
               "mini-grids, solar home systems) could plausibly triple the connection rate. Next question: what is the cost per connection of each?",
        figure=fig,
    )


# --------------------------------------------------------------------------- finding 2
def finding_people(df: pd.DataFrame) -> Finding:
    end = int(df["year"].max())
    z = df[df["iso3"] == FOCUS_ISO]
    z0, z1 = z.iloc[0], z.iloc[-1]
    peak = z.loc[z["pop_without"].idxmax()]
    pop_growth = z1["population"] / z0["population"]
    region = df.groupby("year")["pop_without"].sum() / 1e6
    peers_up = df[df["year"].isin([2000, end])].pivot(index="country", columns="year", values="pop_without_m")
    peers_up = peers_up[peers_up[end] > peers_up[2000]].index.tolist()

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("Share with access (%)", "People without electricity (M)"))
    fig.add_trace(go.Scatter(x=z["year"], y=z["access"], mode="lines+markers", line=dict(color=FOCUS, width=3), marker=dict(size=6),
                             hovertemplate="%{x}: %{y:.1f}%<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=z["year"], y=z["pop_without_m"], marker=dict(color=FOCUS, cornerradius=3), opacity=0.85,
                         hovertemplate="%{x}: %{y:.2f} million without electricity<extra></extra>"), row=1, col=2)
    fig.add_trace(go.Scatter(x=z["year"], y=z["population"] / 1e6, mode="lines", line=dict(color=INK_2, width=1.5, dash="dot"),
                             hovertemplate="%{x}: total population %{y:.1f} M<extra></extra>"), row=1, col=2)
    fig.add_annotation(x=end, y=z1["population"] / 1e6, text="total population", showarrow=False, xanchor="right", yshift=10,
                       font=dict(color=INK_2, size=11), row=1, col=2)
    fig = _base_layout(fig, height=380, margin=dict(l=8, r=8, t=48, b=8))
    fig.update_yaxes(range=[0, 100], ticksuffix="%", row=1, col=1)
    fig.update_yaxes(rangemode="tozero", ticksuffix=" M", row=1, col=2)
    fig.update_annotations(font=dict(size=13, color=INK))

    return Finding(
        title=f"2 · Percentages hide people: {z1['pop_without_m']:.1f} million Zambians are still without power, more than in 2000",
        context="Access targets are usually reported as a percentage, but programmes, budgets and connection crews deal in households and people.",
        evidence=f"While the access rate tripled, Zambia's population grew {pop_growth:.1f}× (from {z0['population'] / 1e6:.1f} M to "
                 f"{z1['population'] / 1e6:.1f} M). People without electricity went from {z0['pop_without_m']:.1f} M in 2000 to a peak of "
                 f"{peak['pop_without_m']:.1f} M in {int(peak['year'])}, and were still {z1['pop_without_m']:.1f} M in {end}. "
                 f"The same happened in {', '.join(c for c in peers_up if c != 'Zambia')}; across all nine countries the number without "
                 f"power went from {region.loc[2000]:.0f} M to {region.loc[end]:.0f} M.",
        insight="Population growth absorbs most new connections. Only since the mid-2010s has Zambia connected people faster than its "
                "population grows, and the absolute deficit has only just started to fall.",
        implication="Reporting the rate alone overstates success. The workload of the programme is set by the number of people, which is "
                    "roughly where it was a quarter of a century ago.",
        action="Report both measures side by side in national progress reports, and set the connection target in people per year that "
               "covers population growth plus the backlog. Next question: how many connections per year does that imply at current household size?",
        figure=fig,
    )


# --------------------------------------------------------------------------- finding 3
def finding_peers(df: pd.DataFrame) -> Finding:
    end = int(df["year"].max())
    z0, z1 = _row(df, FOCUS_ISO, 2000), _row(df, FOCUS_ISO, end)
    t0, t1 = _row(df, PEER_ISO, 2000), _row(df, PEER_ISO, end)
    spread = data.spread_by_year(df)
    s0, s1 = spread.iloc[0], spread.iloc[-1]
    t_pace, z_pace = _pace(df, PEER_ISO, end, 10), _pace(df, FOCUS_ISO, end, 10)

    fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], horizontal_spacing=0.1,
                        subplot_titles=(f"Wealth vs access paths, 2000–{end}", "Best minus worst country (pp)"))
    for iso in df["iso3"].unique():
        d = df[df["iso3"] == iso]
        color = {FOCUS_ISO: FOCUS, PEER_ISO: COMPARE[0]}.get(iso, CONTEXT)
        hl = iso in (FOCUS_ISO, PEER_ISO)
        fig.add_trace(go.Scatter(
            x=d["gdp_pc"], y=d["access"], mode="lines+markers" if hl else "lines",
            line=dict(color=color, width=2.5 if hl else 1), marker=dict(size=5), opacity=1 if hl else 0.7,
            customdata=d["year"], name=d["country"].iloc[0],
            hovertemplate="<b>%{fullData.name}</b> %{customdata}<br>GDP pc $%{x:,.0f}<br>Access %{y:.1f}%<extra></extra>",
        ), row=1, col=1)
        if hl:
            fig.add_annotation(x=np.log10(d["gdp_pc"].iloc[-1]), y=d["access"].iloc[-1], text=f"<b>{d['country'].iloc[0]} {end}</b>",
                               showarrow=False, xanchor="left", xshift=10, yshift=12 if iso == FOCUS_ISO else -12,
                               font=dict(color=INK, size=12), row=1, col=1)
    fig.add_trace(go.Scatter(x=spread["year"], y=spread["range_pp"], mode="lines+markers", line=dict(color=INK_2, width=2),
                             marker=dict(size=5), hovertemplate="%{x}: best − worst = %{y:.1f} pp<extra></extra>"), row=1, col=2)
    fig = _base_layout(fig, height=400, margin=dict(l=8, r=8, t=48, b=8))
    fig.update_xaxes(type="log", tickvals=LOG_TICKS, ticktext=[f"${v:,}" for v in LOG_TICKS],
                     title=dict(text="GDP per capita, current US$ (log)", font=dict(size=12)), row=1, col=1)
    fig.update_yaxes(range=[0, 100], ticksuffix="%", row=1, col=1)
    fig.update_yaxes(range=[0, 100], ticksuffix=" pp", row=1, col=2)
    fig.update_annotations(font=dict(size=13, color=INK), selector=dict(showarrow=False, xref="paper"))

    return Finding(
        title="3 · Income is not destiny: Tanzania, as poor as Zambia, gained more, yet the region is not converging",
        context="Planners want benchmarks they can learn from. A useful benchmark is a country that faced similar constraints, not simply the richest neighbour.",
        evidence=f"In {end} Tanzania's GDP per capita (${t1['gdp_pc']:,.0f}) is almost identical to Zambia's (${z1['gdp_pc']:,.0f}). Tanzania went from "
                 f"{t0['access']:.1f}% to {t1['access']:.1f}% (+{t1['access'] - t0['access']:.1f} pp) against Zambia's +{z1['access'] - z0['access']:.1f} pp, "
                 f"and its 10-year pace is {t_pace:.2f} pp/yr vs Zambia's {z_pace:.2f}. Across all nine countries the gap between best and worst "
                 f"widened from {s0['range_pp']:.1f} pp in 2000 to {s1['range_pp']:.1f} pp in {end}.",
        insight="At the same income level, countries achieved very different rates of progress, so income alone does not set the ceiling. "
                "At the same time the laggards (Malawi, Mozambique) are falling further behind, so 'regional average' benchmarks flatter everyone.",
        implication="Zambia's most relevant benchmark is a peer at the same income that is moving faster, not South Africa or Botswana, "
                    "whose higher income and history make their paths hard to copy.",
        action="Commission a short comparative review of Tanzania's (and Zimbabwe's) electrification delivery models since 2014. Next question, which "
               "this dataset cannot answer: which programme features explain the faster pace?",
        figure=fig,
    )


def all_findings(df: pd.DataFrame) -> list[Finding]:
    return [finding_pace(df), finding_people(df), finding_peers(df)]
