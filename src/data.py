"""Load, clean and derive variables from the World Bank electricity dataset.

Cleaning decisions follow the Assignment 1 dataset audit:
- ISO2 for Namibia is the literal string "NA", so the file is read with
  ``keep_default_na=False`` and ISO3 is used as the country key everywhere.
- ``Region`` is constant (with a trailing space) and ``Period start`` duplicates
  ``Year``; both are dropped.
- Renewable energy is unreported for 2022-2024 and is left missing, never imputed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "world_bank_electricity_development_dataset.xlsx"

SDG_TARGET_YEAR = 2030
RENEWABLES_LAST_YEAR = 2021
MA_WINDOW = 3
# A fall of more than this many percentage points in one year is flagged as a
# likely survey/estimation artefact rather than a real loss of connections.
ANOMALY_DROP_PP = 3.0

INCOME_ORDER = ["Low income", "Lower middle income", "Upper middle income"]

COLUMNS = {
    "Country": "country",
    "ISO2": "iso2",
    "ISO3": "iso3",
    "Region": "region",
    "Income group": "income",
    "Capital city": "capital",
    "Longitude": "lon",
    "Latitude": "lat",
    "Year": "year",
    "Period start": "period_start",
    "Electricity access (% of population)": "access",
    "Renewable energy consumption (% of total final energy consumption)": "renewables",
    "GDP per capita (current US$)": "gdp_pc",
    "Urban population (% of total population)": "urban",
    "Life expectancy at birth (years)": "life_exp",
    "Population, total": "population",
}


def load_raw(path: Path = DATA_PATH) -> pd.DataFrame:
    """Read the Data sheet with "NA" kept as text (Namibia's ISO2)."""
    df = pd.read_excel(path, sheet_name="Data", keep_default_na=False, na_values=[""])
    return df.rename(columns=COLUMNS)


def moving_average(series: pd.Series, k: int = MA_WINDOW) -> pd.Series:
    """Trailing moving average MA_t = (1/k) * sum_{i=0}^{k-1} x_{t-i}."""
    return series.rolling(window=k, min_periods=k).mean()


def required_pp_per_year(access: float, year: int, target_year: int = SDG_TARGET_YEAR) -> float:
    """Percentage points per year needed to go from ``access`` in ``year`` to 100% by ``target_year``."""
    years_left = target_year - year
    if years_left <= 0:
        return np.nan
    return (100.0 - access) / years_left


def trend_pp_per_year(years: pd.Series, values: pd.Series) -> float:
    """Least-squares slope (pp per year). Robust to a single noisy endpoint."""
    if len(years) < 2:
        return np.nan
    slope, _ = np.polyfit(years.astype(float), values.astype(float), 1)
    return float(slope)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw frame and add the derived variables used by the dashboard."""
    df = df.drop(columns=["region", "period_start"]).copy()
    for col in ["country", "iso2", "iso3", "income", "capital"]:
        df[col] = df[col].astype(str).str.strip()
    df["income"] = pd.Categorical(df["income"], categories=INCOME_ORDER, ordered=True)
    df = df.sort_values(["iso3", "year"]).reset_index(drop=True)

    df["pop_without"] = df["population"] * (1 - df["access"] / 100)
    df["pop_with"] = df["population"] * df["access"] / 100
    df["pop_without_m"] = df["pop_without"] / 1e6
    df["log_gdp_pc"] = np.log10(df["gdp_pc"])

    g = df.groupby("iso3", sort=False)
    df["yoy_change"] = g["access"].diff()
    df["access_ma"] = g["access"].transform(moving_average)
    df["pop_without_m_ma"] = g["pop_without_m"].transform(moving_average)
    df["anomaly"] = df["yoy_change"] < -ANOMALY_DROP_PP

    df["rank"] = df.groupby("year")["access"].rank(ascending=False, method="min").astype(int)
    leader = df.groupby("year")["access"].transform("max")
    df["gap_to_leader"] = leader - df["access"]
    df["required_pp_2030"] = [required_pp_per_year(a, y) for a, y in zip(df["access"], df["year"])]
    return df


def load() -> pd.DataFrame:
    return prepare(load_raw())


def country_summary(df: pd.DataFrame, start: int, end: int, pace_years: int = 10) -> pd.DataFrame:
    """One row per country describing the selected window [start, end].

    ``pace_pp_per_year`` is the OLS slope over the last ``pace_years`` years of the
    window, so one noisy endpoint (e.g. Zambia 2014) does not distort the pace.
    """
    rows = []
    for iso3, d in df[(df["year"] >= start) & (df["year"] <= end)].groupby("iso3"):
        d = d.sort_values("year")
        first, last = d.iloc[0], d.iloc[-1]
        recent = d[d["year"] > end - pace_years]
        pace = trend_pp_per_year(recent["year"], recent["access"])
        need = required_pp_per_year(last["access"], int(last["year"]))
        rows.append(
            {
                "iso3": iso3,
                "country": last["country"],
                "income": last["income"],
                "access_start": first["access"],
                "access_end": last["access"],
                "change_pp": last["access"] - first["access"],
                "pop_without_start_m": first["pop_without_m"],
                "pop_without_end_m": last["pop_without_m"],
                "pop_without_change_m": last["pop_without_m"] - first["pop_without_m"],
                "population_end_m": last["population"] / 1e6,
                "gdp_pc_end": last["gdp_pc"],
                "rank_end": int(last["rank"]),
                "gap_to_leader_end": last["gap_to_leader"],
                "pace_pp_per_year": pace,
                "required_pp_per_year": need,
                "year_100pct_at_pace": (
                    int(last["year"] + np.ceil((100 - last["access"]) / pace)) if pace and pace > 0 else None
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("access_end", ascending=False).reset_index(drop=True)


def spread_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Max - min and standard deviation of access across countries, per year (convergence check)."""
    g = df.groupby("year")["access"]
    return pd.DataFrame({"range_pp": g.max() - g.min(), "std_pp": g.std()}).reset_index()
