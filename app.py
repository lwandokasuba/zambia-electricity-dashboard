"""Streamlit entry point: `streamlit run app.py`.

All views read one shared state held in ``st.session_state``:
focus country, comparison countries, income filter, year range and metric.
Clicking a country in the map, ranking or scatter sets the focus country, and
clicking a heatmap cell sets the end year, so the views stay coordinated.
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src import charts, content, data, story

st.set_page_config(page_title="Zambia Electricity Access Benchmark", page_icon="⚡", layout="wide")

FOCUS_KEY, COMPARE_KEY, YEARS_KEY = "focus_iso", "compare_iso", "years"
COUNTRY_CHART_KEYS = ["map_sel", "rank_sel", "scatter_sel"]
HEAT_KEY = "heat_sel"
PLOT_CONFIG = {"displayModeBar": False}


@st.cache_data
def load_data() -> pd.DataFrame:
    return data.load()


df = load_data()
YEAR_MIN, YEAR_MAX = int(df["year"].min()), int(df["year"].max())
NAMES = df.drop_duplicates("iso3").set_index("iso3")["country"].sort_values()
ISO_BY_NAME = {v: k for k, v in NAMES.items()}
ALL_ISO = NAMES.index.tolist()

# ---------------------------------------------------------------- shared state
st.session_state.setdefault(FOCUS_KEY, "ZMB")
st.session_state.setdefault(COMPARE_KEY, ["TZA", "BWA"])
st.session_state.setdefault(YEARS_KEY, (YEAR_MIN, YEAR_MAX))
st.session_state.setdefault("_seen", {})


def _new_points(key: str) -> list[dict]:
    """Points of a chart selection, only if they differ from the last one we acted on."""
    event = st.session_state.get(key)
    if not event:
        return []
    points = list(event.get("selection", {}).get("points", []))
    signature = json.dumps(points, sort_keys=True, default=str)
    if st.session_state["_seen"].get(key) == signature:
        return []
    st.session_state["_seen"][key] = signature
    return points


def _md(text: str) -> str:
    """Escape $ so Streamlit markdown does not render dollar amounts as LaTeX."""
    return text.replace("$", "\\$")


def _iso_from_point(point: dict) -> str | None:
    custom = point.get("customdata")
    if isinstance(custom, (list, tuple)) and custom and custom[0] in ALL_ISO:
        return custom[0]
    if point.get("location") in ALL_ISO:
        return point["location"]
    return None


# Apply chart clicks BEFORE the sidebar widgets are created, so widgets reflect them.
for key in COUNTRY_CHART_KEYS:
    for point in _new_points(key):
        iso = _iso_from_point(point)
        if iso:
            st.session_state[FOCUS_KEY] = iso
            break
for point in _new_points(HEAT_KEY):
    year = int(point.get("x"))
    start, _ = st.session_state[YEARS_KEY]
    st.session_state[YEARS_KEY] = (min(start, year - 2), year)
    break

# A country cannot be both the focus and a comparison. When the focus moves away from
# Zambia (the user's own country), Zambia joins the comparisons so it stays visible.
_focus = st.session_state[FOCUS_KEY]
_compare = [c for c in st.session_state[COMPARE_KEY] if c != _focus]
if _focus != st.session_state.get("_prev_focus", "ZMB") and _focus != "ZMB" and "ZMB" not in _compare:
    _compare = (["ZMB"] + _compare)[:3]
st.session_state[COMPARE_KEY] = _compare
st.session_state["_prev_focus"] = _focus

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Controls")
    focus = st.selectbox("Focus country", ALL_ISO, format_func=NAMES.get, key=FOCUS_KEY,
                         help="Also set by clicking a country on the map, ranking or scatter.")
    compare = st.multiselect("Compare with (max 3)", [i for i in ALL_ISO if i != focus], format_func=NAMES.get,
                             key=COMPARE_KEY, max_selections=3)
    incomes = st.multiselect("Income groups shown as context", data.INCOME_ORDER, default=data.INCOME_ORDER,
                             help="Grey context countries are limited to these tiers. Focus and comparison countries are always shown.")
    start, end = st.slider("Years", YEAR_MIN, YEAR_MAX, key=YEARS_KEY,
                           help="Window for change, pace and trails; the end year drives the map, ranking and KPIs.")
    if end - start < 2:
        st.warning("Choose a window of at least 3 years.")
        st.stop()
    metric = st.radio("Measure", ["access", "without"], format_func=lambda m: charts.METRICS[m]["short"],
                      help="Rate vs count: % of population with access, or the number of people without it.")
    show_ma = st.toggle("3-year moving average", value=False, help="Adds a smoothed trend; the raw series stays visible.")
    st.caption("Data: World Bank WDI (indicators updated 13 July 2026). CC BY 4.0.")

visible = sorted(set(df.loc[df["income"].isin(incomes), "iso3"]) | {focus} | set(compare))
window = df[df["year"].between(start, end)]
summary = data.country_summary(df, start, end)
f = summary.set_index("iso3").loc[focus]
focus_name = NAMES[focus]

# ---------------------------------------------------------------- header
st.markdown(f"## {content.TITLE}")
st.markdown(f"<span style='color:#52514e'>{content.USER_STATEMENT}</span>", unsafe_allow_html=True)

tab_explore, tab_story, tab_limits, tab_about = st.tabs(
    ["Explore", "Story: 3 findings", "Limitations & ethics", "About this dashboard"]
)

with tab_explore:
    st.subheader(f"{focus_name}, {end}")
    k = st.columns(3) + st.columns(3)
    neutral = dict(delta_color="off", delta_arrow="off", border=True)
    k[0].metric("Access", f"{f['access_end']:.1f}%", f"{f['change_pp']:+.1f} pp", border=True,
                help=f"Share of the population with electricity in {end}. Delta: change since {start}.")
    k[1].metric("Rank of 9", f"{f['rank_end']}", "leader" if f["rank_end"] == 1 else f"{f['gap_to_leader_end']:.1f} pp behind",
                help=f"Rank by access in {end}; delta is the gap to the leading country.", **neutral)
    k[2].metric("No electricity", f"{f['pop_without_end_m']:.2f} M", f"{f['pop_without_change_m']:+.2f} M",
                delta_color="inverse", border=True,
                help=f"People without electricity in {end} = population × (1 − access). Delta: change since {start}.")
    k[3].metric("Pace, pp/yr", f"{f['pace_pp_per_year']:.2f}", "10-yr trend",
                help="Least-squares slope of access over the last 10 years of the window.", **neutral)
    need = f["required_pp_per_year"]
    if pd.notna(need):
        k[4].metric("Needed, pp/yr", f"{need:.2f}",
                    f"{need / f['pace_pp_per_year']:.1f}× pace" if f["pace_pp_per_year"] > 0 else "pace not positive",
                    help=f"Percentage points per year needed to go from {end} to 100% by 2030 (SDG 7.1).", **neutral)
    k[5].metric("100% reached", str(f["year_100pct_at_pace"] or "—"), "at current pace",
                help="Naive linear extrapolation of the recent pace; not a forecast.", **neutral)

    c1, c2 = st.columns([5, 7])
    with c1:
        st.plotly_chart(charts.map_figure(df[df["year"] == end], metric, focus, compare), key="map_sel",
                        on_select="rerun", selection_mode="points", config=PLOT_CONFIG, width="stretch")
        st.caption("Click a country or bubble to make it the focus. Bubble size = population.")
    with c2:
        st.plotly_chart(charts.timeseries_figure(window, metric, focus, compare, visible, show_ma),
                        config=PLOT_CONFIG, width="stretch")
        st.caption("Focus in orange, comparisons in colour, other countries in grey. ✕ marks one-year drops > 3 pp. Drag to zoom, double-click to reset.")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(charts.scatter_figure(df, start, end, focus, compare, visible), key="scatter_sel",
                        on_select="rerun", selection_mode="points", config=PLOT_CONFIG, width="stretch")
    with c4:
        rank_mode = st.selectbox(
            "Rank countries by",
            ["access_end", "change_pp", "pop_without_end_m", "pace_pp_per_year"],
            index=2 if metric == "without" else 0,
            format_func={"access_end": "Access level", "change_pp": "Change over the window",
                         "pop_without_end_m": "People without electricity",
                         "pace_pp_per_year": "Recent pace vs 2030 requirement"}.get,
        )
        st.plotly_chart(charts.ranking_figure(summary[summary["iso3"].isin(visible)], rank_mode, focus, compare, start, end),
                        key="rank_sel", on_select="rerun", selection_mode="points", config=PLOT_CONFIG, width="stretch")

    st.plotly_chart(charts.anomaly_heatmap(df, visible, focus, end), key=HEAT_KEY, on_select="rerun",
                    selection_mode="points", config=PLOT_CONFIG, width="stretch")
    st.caption("The outlined column is the current end year. Click a cell to make that year the end of the window (map, ranking, scatter and KPIs follow). "
               "Drops marked ▼ are more likely survey revisions than real disconnections; see Limitations.")

    with st.expander("Data table for the current selection"):
        cols = {"country": "Country", "year": "Year", "income": "Income group", "access": "Access (%)",
                "pop_without_m": "Without electricity (M)", "population": "Population", "gdp_pc": "GDP per capita (US$)",
                "urban": "Urban (%)", "yoy_change": "Change vs prior year (pp)", "anomaly": "Flagged drop"}
        table = window[window["iso3"].isin(visible)][list(cols)].rename(columns=cols)
        st.dataframe(table, hide_index=True, width="stretch")
        st.download_button("Download CSV", table.to_csv(index=False).encode(), "electricity_access_selection.csv", "text/csv")

with tab_story:
    st.caption("Three findings, each told as Context → Evidence → Insight → Implication → Recommended action. Numbers are computed live from the data.")
    for finding in story.all_findings(df):
        st.subheader(finding.title)
        left, right = st.columns([5, 7])
        with left:
            for label, text in [("Context", finding.context), ("Evidence", finding.evidence),
                                ("Insight", finding.insight), ("Implication", finding.implication)]:
                st.markdown(f"**{label}.** {_md(text)}")
            st.info(f"**Recommended action / next question.** {_md(finding.action)}")
        with right:
            st.plotly_chart(finding.figure, config=PLOT_CONFIG, width="stretch")
        st.divider()

with tab_limits:
    st.subheader("What this dashboard cannot tell you")
    for item in content.CANNOT_SUPPORT:
        st.error(_md(item))
    cols = st.columns(2)
    for i, (heading, items) in enumerate(content.LIMITATIONS.items()):
        with cols[i % 2]:
            st.markdown(f"#### {heading}")
            st.markdown("\n".join(f"- {_md(x)}" for x in items))
    flagged = df[df["anomaly"]][["country", "year", "yoy_change"]].rename(
        columns={"country": "Country", "year": "Year", "yoy_change": "Change vs prior year (pp)"})
    st.markdown("#### One-year drops of more than 3 pp (flagged, not removed)")
    st.dataframe(flagged, hide_index=True)

with tab_about:
    st.subheader("Users")
    st.markdown("\n".join(f"- {u}" for u in content.USERS))
    a, b = st.columns(2)
    with a:
        st.subheader("Questions it answers")
        st.markdown("\n".join(f"{i}. {q}" for i, q in enumerate(content.QUESTIONS, 1)))
    with b:
        st.subheader("Decisions it supports")
        st.markdown("\n".join(f"- {d}" for d in content.DECISIONS))
    st.subheader("Interactions and their analytical purpose")
    rows = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in content.INTERACTIONS)
    st.markdown("| Interaction | Where | Analytical purpose |\n|---|---|---|\n" + rows)
    st.subheader("Data")
    st.markdown(
        "World Bank World Development Indicators via the World Bank API: EG.ELC.ACCS.ZS, EG.FEC.RNEW.ZS, NY.GDP.PCAP.CD, "
        "SP.URB.TOTL.IN.ZS, SP.DYN.LE00.IN, SP.POP.TOTL, for Zambia, Angola, Botswana, Malawi, Mozambique, Namibia, South Africa, "
        "Tanzania and Zimbabwe, 2000–2024 (225 country-years). Derived: people without electricity = population × (1 − access/100); "
        "pace = least-squares slope over the last 10 years of the window; needed pace = (100 − access) / (2030 − year); "
        "3-year moving average MAₜ = (xₜ + xₜ₋₁ + xₜ₋₂)/3."
    )
