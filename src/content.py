"""Static text shared by the app and the written report (Tasks 1, 3 and 6)."""

TITLE = "Powering Zambia: Electricity Access Benchmark, 2000–2024"

USER_STATEMENT = (
    "The dashboard is designed for planners at Zambia's Ministry of Energy and Rural Electrification "
    "Authority. They need to benchmark Zambia's electricity-access progress against eight regional "
    "peers, size the remaining gap in people rather than percentages, and judge whether the current "
    "pace is enough for SDG 7 universal access by 2030."
)

USERS = [
    "Primary: energy planners and analysts at the Ministry of Energy and the Rural Electrification Authority (REA).",
    "Secondary: development partners who co-finance Zambian electrification and read the same benchmark.",
]

QUESTIONS = [
    "Where does Zambia rank today, and how far is it behind the regional leaders?",
    "Is Zambia's recent pace (percentage points per year) enough to reach 100% access by 2030, and how much faster would it need to be?",
    "How many Zambians still lack electricity, and is that number actually falling even though the percentage is rising?",
    "Which peers made the biggest gains from a similar starting point or income level?",
    "Is Zambia's access above or below what its GDP per capita would suggest?",
    "Which year-to-year jumps are likely data artefacts rather than real change?",
]

DECISIONS = [
    "Set a realistic annual connection target (pp per year, and people per year) instead of an aspirational one.",
    "Choose which peer countries to study as policy benchmarks (e.g. a peer at the same income level that moved faster).",
    "Frame budgets and programmes in people to connect, not only in percentage points, because population growth absorbs progress.",
    "Flag suspect data points for validation with ZamStats / ERB before they are quoted in official reporting.",
]

# (interaction, where, analytical purpose) - Task 3
INTERACTIONS = [
    ("Click a country (map, bar chart or scatter)", "All views",
     "Sets the focus country. KPIs, the time series, the scatter trail and the ranking highlight all update, so the planner can "
     "swap Zambia for a peer and read that peer's whole story in the same layout (coordinated views: Selection_map → Filter_time → Filter_scatter/bar)."),
    ("Focus country selector", "Sidebar",
     "Keyboard-accessible version of the click above; Zambia is the default because it is the user's own country."),
    ("Comparison countries (max 3)", "Sidebar",
     "Gives up to three named peers their own colour while the rest stay grey, so benchmarking is against chosen peers, not a nine-line tangle."),
    ("Income-group filter", "Sidebar",
     "Category selection: restricts the context countries to a development tier, so Zambia can be compared with lower-middle-income peers only."),
    ("Year-range slider", "Sidebar",
     "Date selection: sets the window for change, pace and trails, and the end year for the map, ranking and KPIs. Lets the planner test whether "
     "conclusions hold for e.g. the SDG period (2015–2024) as well as the full series."),
    ("Metric toggle: % access ↔ people without electricity", "Map, time series, ranking",
     "Switches between a rate and an absolute count (Assignment 3: rates vs counts). Reveals that a rising % can coexist with a rising number of people left out."),
    ("3-year moving-average toggle", "Time series",
     "Smooths survey noise to show the underlying trend; the raw line stays visible so the reader also sees what smoothing hides (e.g. the 2007 dip)."),
    ("Ranking measure selector", "Bar chart",
     "Ranks by level, by change, by people without power or by pace vs the 2030 requirement; each ranking answers a different planning question."),
    ("Click a heatmap cell", "Anomaly heatmap",
     "Drill-down: jumps the end year to that cell so an anomaly can be inspected in the cross-section (map, ranking, scatter) for that year."),
    ("Hover tooltips", "All charts",
     "Details on demand: exact values, change vs prior year, population and income group without cluttering the charts with labels."),
    ("Zoom / pan", "Time series",
     "Lets the analyst zoom into a short period (e.g. 2005–2010) to inspect noisy years."),
]

LIMITATIONS = {
    "Limitations of the dataset": [
        "Nine countries, purposively chosen around Zambia; results do not generalise to Sub-Saharan Africa as a whole.",
        "National averages only: no provincial, district, rural/urban or household-level detail.",
        "Income group is today's World Bank classification applied to all 25 years, not a historical series.",
        "GDP per capita is in current US$, so it moves with inflation and exchange rates (e.g. Zambia's fall from about $1,800 in 2013 to $950 in 2020 coincides with a weaker kwacha, so it is not a like-for-like fall in output).",
    ],
    "Uncertainty": [
        "WDI electricity-access values are modelled estimates built from periodic household surveys and censuses, interpolated between survey years. "
        "Year-to-year movements are therefore uncertain, and sudden drops (Zambia 2007 and 2010, Zimbabwe 2014, Malawi 2019) are more likely revisions "
        "or survey changes than real disconnections. They are flagged (▼) rather than removed.",
        "The 'pace' is a 10-year linear trend; the 2030 continuation is a naive extrapolation and is shown with a band built from 5- and 15-year trends to make the sensitivity visible.",
        "'Access' in WDI includes off-grid solar and mini-grids and says nothing about reliability, hours of supply or affordability (load-shedding is invisible here).",
    ],
    "Missing data": [
        "Renewable energy share is unreported for 2022–2024 (World Bank publication lag); it is not imputed and is not used in the dashboard's findings.",
        "No data on electrification programmes, investment, tariffs or connection costs, so the dashboard cannot explain why access changed.",
    ],
    "Possible bias": [
        "Survey timing differs between countries, so differences in a given year partly reflect when each country last surveyed.",
        "Purposive country selection centred on Zambia may frame Zambia as 'middle of the pack' simply because of which peers were chosen.",
        "Percentages favour small countries in rankings; the people-without-electricity view counters this but in turn emphasises populous countries.",
    ],
    "Potentially misleading interpretations": [
        "Ranks exaggerate tiny differences: Zambia (53.6%) and Tanzania (52.4%) differ by about 1 pp, well within estimation error, yet occupy different ranks.",
        "The moving average hides single-year shocks; always read it with the raw line.",
        "The log GDP axis compresses large differences in wealth; equal horizontal distances are equal ratios, not equal dollar gaps.",
        "The GDP–access association is correlation across countries; it is not evidence that growth causes access or vice versa.",
    ],
    "Privacy": [
        "All data are public national aggregates (World Bank WDI, CC BY 4.0); no personal or household data are processed.",
        "Extending the dashboard to household-survey or utility-customer data would require anonymisation and aggregation thresholds before display.",
    ],
}

CANNOT_SUPPORT = [
    "That GDP growth, or any specific policy (e.g. Tanzania's rural programme), caused the gains seen here: the data are observational and contain no policy variables.",
    "Which Zambian provinces or districts to prioritise: there is no sub-national data.",
    "A firm forecast that Zambia will reach a given level in 2030: the projection is a naive trend on modelled, revised estimates.",
]
