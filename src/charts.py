"""Plotly figure builders for the Explore tab.

Colour rules (validated with the dataviz palette checker, light surface):
- the focus country is always ORANGE, up to three comparison countries take
  BLUE / AQUA / VIOLET in selection order, every other country is recessive GREY;
- magnitude maps use one-hue sequential ramps (blue for % access, orange for
  people without electricity);
- year-on-year change uses a diverging red <-> grey <-> blue scale centred on 0.
Every chart carries ISO3 in ``customdata`` so a click can drive the shared focus.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

FOCUS = "#eb6834"
COMPARE = ["#2a78d6", "#1baf7a", "#4a3aa7"]
CONTEXT = "#c3c2b7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
LOG_TICKS = [250, 500, 1000, 2000, 4000, 8000]

BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ORANGES = ["#fde3d6", "#f8bfa3", "#f39a70", "#eb6834", "#c94e1f", "#9a3a15", "#6b280e"]
DIVERGING = [[0.0, "#b3261e"], [0.35, "#e34948"], [0.5, "#f0efec"], [0.65, "#3987e5"], [1.0, "#104281"]]

METRICS = {
    "access": {
        "label": "Electricity access (% of population)",
        "short": "Access (%)",
        "col": "access",
        "ma_col": "access_ma",
        "fmt": ".1f",
        "suffix": "%",
        "scale": BLUES,
    },
    "without": {
        "label": "People without electricity (millions)",
        "short": "Without electricity (M)",
        "col": "pop_without_m",
        "ma_col": "pop_without_m_ma",
        "fmt": ".2f",
        "suffix": " M",
        "scale": ORANGES,
    },
}


def color_map(focus: str, compare: list[str]) -> dict[str, str]:
    """ISO3 -> colour. Focus wins over comparison if a country is in both."""
    colors = {iso: COMPARE[i] for i, iso in enumerate([c for c in compare if c != focus][: len(COMPARE)])}
    colors[focus] = FOCUS
    return colors


def _base_layout(fig: go.Figure, height: int = 380, **kw) -> go.Figure:
    title = dict(font=dict(size=15, color=INK), x=0, xanchor="left", y=0.98) | kw.pop("title", {})
    layout = dict(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=SURFACE,
        font=dict(family="Inter, -apple-system, Segoe UI, Roboto, sans-serif", size=13, color=INK_2),
        title=title,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=12)),
        showlegend=False,
        clickmode="event+select",
        dragmode=False,
    )
    fig.update_layout(layout | kw)
    fig.update_xaxes(gridcolor=GRID, linecolor=CONTEXT, tickcolor=CONTEXT, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=CONTEXT, tickcolor=CONTEXT, zeroline=False, tickfont=dict(color=MUTED))
    return fig


# --------------------------------------------------------------------------- map
def map_figure(df_year: pd.DataFrame, metric: str, focus: str, compare: list[str]) -> go.Figure:
    m = METRICS[metric]
    colors = color_map(focus, compare)
    d = df_year.copy()
    custom = np.stack([d["iso3"], d["country"], d["access"], d["pop_without_m"], d["population"] / 1e6], axis=-1)
    hover = (
        "<b>%{customdata[1]}</b><br>Access: %{customdata[2]:.1f}%<br>"
        "Without electricity: %{customdata[3]:.2f} M<br>Population: %{customdata[4]:.1f} M<extra></extra>"
    )
    fig = go.Figure()
    fig.add_trace(
        go.Choropleth(
            locations=d["iso3"],
            z=d[m["col"]],
            customdata=custom,
            hovertemplate=hover,
            colorscale=[[i / (len(m["scale"]) - 1), c] for i, c in enumerate(m["scale"])],
            zmin=0,
            zmax=100 if metric == "access" else float(d[m["col"]].max()),
            # On the orange "people without" ramp an orange outline would vanish, so the focus is outlined in ink.
            marker_line_color=[(INK if metric == "without" and i == focus else colors.get(i, "white")) for i in d["iso3"]],
            marker_line_width=[3 if i in colors else 0.8 for i in d["iso3"]],
            colorbar=dict(title=dict(text=m["short"], side="top"), orientation="h", thickness=10, len=0.7, x=0.5, y=-0.02,
                          xanchor="center", yanchor="top", outlinewidth=0),
        )
    )
    # Proportional symbols at the capital: population size, so the reader can see
    # that a mid-ranked % (e.g. Tanzania) still means the largest absolute deficit.
    size = 8 + 32 * np.sqrt(d["population"] / d["population"].max())
    fig.add_trace(
        go.Scattergeo(
            lon=d["lon"],
            lat=d["lat"],
            customdata=custom,
            hovertemplate=hover,
            mode="markers",
            marker=dict(
                size=size,
                color=[colors.get(i, "rgba(255,255,255,0.0)") for i in d["iso3"]],
                opacity=0.85,
                line=dict(color=[colors.get(i, INK_2) for i in d["iso3"]], width=1.5),
            ),
        )
    )
    fig.update_geos(
        scope="africa",
        fitbounds="locations",
        visible=False,
        showcountries=True,
        countrycolor="white",
        showland=True,
        landcolor="#f0efec",
        bgcolor="rgba(0,0,0,0)",
        projection_type="mercator",
    )
    return _base_layout(fig, height=420, title=dict(text=f"{m['label']}, {int(d['year'].iloc[0])}"))


# --------------------------------------------------------------------------- time series
def _declutter(labels: list[list], min_gap: float) -> list[list]:
    """Push end-of-line labels apart vertically so direct labels never overlap."""
    labels = sorted(labels, key=lambda l: l[2])
    for i in range(1, len(labels)):
        if labels[i][2] - labels[i - 1][2] < min_gap:
            labels[i][2] = labels[i - 1][2] + min_gap
    return labels


def timeseries_figure(
    df: pd.DataFrame, metric: str, focus: str, compare: list[str], visible: list[str], show_ma: bool
) -> go.Figure:
    m = METRICS[metric]
    colors = color_map(focus, compare)
    fig = go.Figure()
    labels: list[list] = []
    # Context first so highlighted lines draw on top.
    order = [i for i in visible if i not in colors] + [i for i in colors if i != focus] + [focus]
    for iso in order:
        d = df[df["iso3"] == iso]
        if d.empty:
            continue
        name = d["country"].iloc[0]
        color = colors.get(iso, CONTEXT)
        highlighted = iso in colors
        custom = np.stack([d["iso3"], d["country"], d["yoy_change"].fillna(0)], axis=-1)
        fig.add_trace(
            go.Scatter(
                x=d["year"],
                y=d[m["col"]],
                customdata=custom,
                name=name,
                mode="lines+markers" if highlighted else "lines",
                line=dict(color=color, width=3 if iso == focus else (2 if highlighted else 1.2)),
                marker=dict(size=8 if iso == focus else 6, color=color, line=dict(color=SURFACE, width=1.5)),
                opacity=1.0 if (highlighted and not show_ma) or iso == focus else (0.45 if show_ma else 0.9),
                hovertemplate=f"<b>%{{customdata[1]}}</b> %{{x}}<br>{m['short']}: %{{y:{m['fmt']}}}{m['suffix']}"
                + ("<br>Change vs prior year: %{customdata[2]:+.1f} pp" if metric == "access" else "")
                + "<extra></extra>",
            )
        )
        if show_ma and highlighted:
            fig.add_trace(
                go.Scatter(
                    x=d["year"],
                    y=d[m["ma_col"]],
                    mode="lines",
                    line=dict(color=color, width=3, dash="dash"),
                    hovertemplate=f"{name} %{{x}}<br>3-yr moving average: %{{y:{m['fmt']}}}{m['suffix']}<extra></extra>",
                )
            )
        if highlighted:
            last = d.iloc[-1]
            labels.append([name, last["year"], last[m["col"]]])
    span = 100 if metric == "access" else float(df[m["col"]].max())
    for name, x, y in _declutter(labels, min_gap=0.06 * span):
        fig.add_annotation(x=x, y=y, text=f"<b>{name}</b>", showarrow=False, xanchor="left", xshift=8,
                           font=dict(color=INK, size=12))
    if metric == "access":
        a = df[(df["iso3"] == focus) & df["anomaly"]]
        if not a.empty:
            fig.add_trace(
                go.Scatter(
                    x=a["year"], y=a["access"], mode="markers",
                    marker=dict(symbol="x-thin", size=14, line=dict(color=INK, width=2)),
                    hovertemplate="Drop of %{customdata:.1f} pp in one year — likely survey/estimation artefact<extra></extra>",
                    customdata=a["yoy_change"],
                )
            )
    title = m["label"] + (" · dashed = 3-yr average" if show_ma else "")
    fig = _base_layout(fig, height=420, title=dict(text=title), margin=dict(l=8, r=84, t=36, b=8))
    fig.update_layout(dragmode="zoom", hovermode="closest")
    fig.update_xaxes(title=None, dtick=4, range=[df["year"].min() - 0.5, df["year"].max() + 0.5])
    fig.update_yaxes(title=None, rangemode="tozero", ticksuffix="%" if metric == "access" else " M")
    if metric == "access":
        fig.update_yaxes(range=[0, 100])
    return fig


# --------------------------------------------------------------------------- scatter
def scatter_figure(df: pd.DataFrame, start: int, end: int, focus: str, compare: list[str], visible: list[str]) -> go.Figure:
    colors = color_map(focus, compare)
    fig = go.Figure()
    # Trails for highlighted countries: how each moved through (wealth, access) space.
    for iso, color in colors.items():
        t = df[(df["iso3"] == iso) & df["year"].between(start, end)]
        if t.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=t["gdp_pc"], y=t["access"], mode="lines+markers",
                line=dict(color=color, width=2 if iso == focus else 1.5),
                marker=dict(size=5, color=color),
                opacity=1 if iso == focus else 0.7,
                customdata=np.stack([t["iso3"], t["country"], t["year"]], axis=-1),
                hovertemplate="<b>%{customdata[1]}</b> %{customdata[2]}<br>GDP pc: $%{x:,.0f}<br>Access: %{y:.1f}%<extra></extra>",
            )
        )
    d = df[(df["year"] == end) & df["iso3"].isin(visible)]
    size = 10 + 30 * np.sqrt(d["population"] / df["population"].max())
    # Direct labels only on highlighted countries (others are named on hover): focus above,
    # comparisons below, so near-identical points such as Zambia and Tanzania stay readable.
    positions = ["top center" if i == focus else "bottom center" for i in d["iso3"]]
    fig.add_trace(
        go.Scatter(
            x=d["gdp_pc"], y=d["access"], mode="markers+text",
            text=[f"<b>{c}</b>" if i in colors else "" for i, c in zip(d["iso3"], d["country"])],
            textposition=positions, textfont=dict(size=12, color=INK), cliponaxis=False,
            marker=dict(size=size, color=[colors.get(i, CONTEXT) for i in d["iso3"]], line=dict(color=SURFACE, width=2)),
            customdata=np.stack([d["iso3"], d["country"], d["population"] / 1e6, d["income"].astype(str)], axis=-1),
            hovertemplate=(
                "<b>%{customdata[1]}</b> (" + str(end) + ")<br>%{customdata[3]}<br>GDP pc: $%{x:,.0f}"
                "<br>Access: %{y:.1f}%<br>Population: %{customdata[2]:.1f} M<extra></extra>"
            ),
        )
    )
    fig = _base_layout(fig, height=420, title=dict(text=f"Wealth vs access, {end}"))
    fig.update_xaxes(type="log", title=dict(text="GDP per capita, current US$ (log scale)", font=dict(size=12)),
                     tickvals=LOG_TICKS, ticktext=[f"${v:,}" for v in LOG_TICKS])
    fig.update_yaxes(title=None, range=[0, 105], ticksuffix="%")
    return fig


# --------------------------------------------------------------------------- ranking
def ranking_figure(summary: pd.DataFrame, mode: str, focus: str, compare: list[str], start: int, end: int) -> go.Figure:
    colors = color_map(focus, compare)
    spec = {
        "access_end": (f"Access in {end} (%)", "%{x:.1f}%", "%"),
        "change_pp": (f"Change in access {start}–{end} (pp)", "%{x:+.1f} pp", " pp"),
        "pop_without_end_m": (f"People without electricity in {end} (M)", "%{x:.2f} M", " M"),
        "pace_pp_per_year": ("Recent pace (bar) vs pace needed for 2030 (|), pp/yr", "%{x:.2f} pp/yr", ""),
    }[mode]
    s = summary.sort_values(mode, ascending=True)
    fig = go.Figure(
        go.Bar(
            y=s["country"], x=s[mode], orientation="h",
            marker=dict(color=[colors.get(i, CONTEXT) for i in s["iso3"]], line=dict(color=SURFACE, width=2), cornerradius=4),
            text=[f"{v:.1f}" if mode != "pop_without_end_m" else f"{v:.2f}" for v in s[mode]],
            textposition="outside", textfont=dict(color=INK_2, size=12), cliponaxis=False,
            customdata=np.stack([s["iso3"], s["country"]], axis=-1),
            hovertemplate="<b>%{customdata[1]}</b><br>" + spec[1] + "<extra></extra>",
        )
    )
    if mode == "pace_pp_per_year":
        fig.add_trace(
            go.Scatter(
                y=s["country"], x=s["required_pp_per_year"], mode="markers",
                marker=dict(symbol="line-ns", size=18, line=dict(color=INK, width=2.5)),
                customdata=np.stack([s["iso3"], s["country"]], axis=-1),
                hovertemplate="<b>%{customdata[1]}</b><br>Needed for 100% by 2030: %{x:.2f} pp/yr<extra></extra>",
            )
        )
    fig = _base_layout(fig, height=420, title=dict(text=spec[0]), bargap=0.25, margin=dict(l=8, r=40, t=36, b=8))
    fig.update_xaxes(title=None, ticksuffix=spec[2])
    if mode == "access_end":
        fig.update_xaxes(range=[0, 100], dtick=20)
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK_2))
    return fig


# --------------------------------------------------------------------------- anomaly heatmap
def anomaly_heatmap(df: pd.DataFrame, visible: list[str], focus: str, end: int) -> go.Figure:
    """Always shows every year (it is the overview used to pick a year); the current end year is outlined."""
    d = df[df["iso3"].isin(visible) & df["yoy_change"].notna()]
    order = d[d["year"] == end].sort_values("access")["country"].tolist()
    z = d.pivot(index="country", columns="year", values="yoy_change").reindex(order)
    iso = d.pivot(index="country", columns="year", values="iso3").reindex(order)
    text = np.where(z.values < -3.0, "▼", "")
    years = np.tile(z.columns.values, (len(z), 1))
    fig = go.Figure(
        go.Heatmap(
            z=z.values, x=z.columns, y=z.index, colorscale=DIVERGING, zmid=0, zmin=-10, zmax=10,
            text=text, texttemplate="%{text}", textfont=dict(color="white", size=11),
            xgap=2, ygap=2,
            customdata=np.dstack([iso.values, years]),
            hovertemplate="<b>%{y}</b> %{x}<br>Change vs prior year: %{z:+.1f} pp<extra></extra>",
            colorbar=dict(title=dict(text="pp", side="right"), thickness=10, outlinewidth=0, ticksuffix=""),
        )
    )
    fig.update_traces(hoverinfo="skip", hovertemplate=None, selector=dict(type="heatmap"))
    # Heatmap traces are not selectable in Plotly, so an invisible marker per cell
    # carries the hover and the click (drill-down to that year).
    cells = d[d["country"].isin(order)]
    fig.add_trace(
        go.Scatter(
            x=cells["year"], y=cells["country"], mode="markers",
            marker=dict(symbol="square", size=14, color="rgba(0,0,0,0)"),
            selected=dict(marker=dict(opacity=0)), unselected=dict(marker=dict(opacity=0)),
            customdata=np.stack([cells["iso3"], cells["yoy_change"]], axis=-1),
            hovertemplate="<b>%{y}</b> %{x}<br>Change vs prior year: %{customdata[1]:+.1f} pp<br>Click to view this year<extra></extra>",
        )
    )
    focus_name = df.loc[df["iso3"] == focus, "country"].iloc[0]
    fig = _base_layout(fig, height=360, title=dict(text="Year-on-year change in access (pp) · ▼ = drop of more than 3 pp"))
    fig.update_layout(hovermode="closest")
    fig.add_vrect(x0=end - 0.5, x1=end + 0.5, line=dict(color=INK, width=2), fillcolor="rgba(0,0,0,0)")
    fig.update_xaxes(dtick=2, gridcolor="rgba(0,0,0,0)", range=[d["year"].min() - 0.5, d["year"].max() + 0.5])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK_2))
    if focus_name in order:
        fig.update_yaxes(
            tickvals=order, ticktext=[f"<b>{c}</b>" if c == focus_name else c for c in order]
        )
    return fig
