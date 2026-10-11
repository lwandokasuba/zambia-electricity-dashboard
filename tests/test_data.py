import math

import pandas as pd
import pytest

from src import data


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return data.load()


def test_balanced_panel(df):
    assert len(df) == 225
    assert df["iso3"].nunique() == 9
    assert df.groupby("iso3")["year"].agg(["min", "max", "count"]).eq([2000, 2024, 25]).all().all()
    assert not df.duplicated(["iso3", "year"]).any()


def test_namibia_iso2_is_not_missing(df):
    assert set(df.loc[df["iso3"] == "NAM", "iso2"]) == {"NA"}


def test_only_renewables_after_2021_are_missing(df):
    core = ["access", "gdp_pc", "urban", "life_exp", "population"]
    assert df[core].notna().all().all()
    missing = df[df["renewables"].isna()]
    assert len(missing) == 26
    assert missing["year"].min() == 2022


def test_population_without_electricity(df):
    zmb_2024 = df[(df["iso3"] == "ZMB") & (df["year"] == 2024)].iloc[0]
    expected = zmb_2024["population"] * (1 - zmb_2024["access"] / 100)
    assert zmb_2024["pop_without"] == pytest.approx(expected)
    assert zmb_2024["pop_with"] + zmb_2024["pop_without"] == pytest.approx(zmb_2024["population"])


def test_required_pace_to_2030():
    assert data.required_pp_per_year(53.6, 2024) == pytest.approx((100 - 53.6) / 6)
    assert math.isnan(data.required_pp_per_year(80, 2030))


def test_moving_average_is_trailing():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])
    ma = data.moving_average(s, k=3)
    assert ma.isna().tolist()[:2] == [True, True]
    assert ma.iloc[2] == pytest.approx(2.0)
    assert ma.iloc[3] == pytest.approx(3.0)


def test_zambia_2007_drop_is_flagged(df):
    row = df[(df["iso3"] == "ZMB") & (df["year"] == 2007)].iloc[0]
    assert row["yoy_change"] == pytest.approx(18.5 - 24.1)
    assert bool(row["anomaly"])


def test_rank_and_gap(df):
    y2024 = df[df["year"] == 2024].set_index("iso3")
    assert y2024.loc["ZAF", "rank"] == 1
    assert y2024.loc["ZAF", "gap_to_leader"] == 0
    assert y2024.loc["MWI", "rank"] == 9


def test_country_summary_window(df):
    s = data.country_summary(df, 2000, 2024).set_index("iso3")
    assert s.loc["ZMB", "change_pp"] == pytest.approx(53.6 - 16.7)
    assert s.loc["ZMB", "pace_pp_per_year"] < s.loc["ZMB", "required_pp_per_year"]
    assert s.loc["ZMB", "pop_without_change_m"] > 0  # more Zambians without power than in 2000
