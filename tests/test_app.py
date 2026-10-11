from streamlit.testing.v1 import AppTest


def _run(**state) -> AppTest:
    at = AppTest.from_file("../app.py", default_timeout=60)
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def test_app_renders_without_errors():
    at = _run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Explore", "Story: 3 findings", "Limitations & ethics", "About this dashboard"]
    assert at.metric[0].value == "53.6%"


def test_focus_change_keeps_zambia_as_comparison():
    at = _run()
    at.selectbox(key="focus_iso").set_value("TZA").run()
    assert not at.exception
    assert at.session_state["focus_iso"] == "TZA"
    assert "ZMB" in at.session_state["compare_iso"]
    assert "TZA" not in at.session_state["compare_iso"]
    assert at.metric[0].value == "52.4%"


def test_people_without_metric_and_moving_average():
    at = _run()
    at.radio[0].set_value("without").run()
    at.toggle[0].set_value(True).run()
    assert not at.exception
