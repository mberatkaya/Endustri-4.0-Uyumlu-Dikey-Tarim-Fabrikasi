from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_login_screen_and_invalid_credentials(monkeypatch):
    monkeypatch.setenv("PANEL_DATA_MODE", "fake")
    monkeypatch.setenv("PREDICTION_MODE", "fake")
    app_path = Path(__file__).resolve().parents[2] / "projeuyp" / "app.py"

    app = AppTest.from_file(str(app_path), default_timeout=15).run()
    assert len(app.text_input) == 2
    assert app.text_input[0].label == "Kullanıcı Adı"
    assert app.text_input[1].label == "Şifre"

    app.text_input[0].input("unknown")
    app.text_input[1].input("wrong")
    app.button[0].click().run()

    assert any("Geçersiz kullanıcı adı" in error.value for error in app.error)


def test_dashboard_operator_login(monkeypatch):
    monkeypatch.setenv("PANEL_DATA_MODE", "fake")
    monkeypatch.setenv("PREDICTION_MODE", "fake")
    app_path = Path(__file__).resolve().parents[2] / "projeuyp" / "app.py"

    app = AppTest.from_file(str(app_path), default_timeout=15).run()
    app.text_input[0].input("operator")
    app.text_input[1].input("123")
    app.button[0].click().run()

    assert app.session_state["auth"]["logged_in"] is True
    assert app.session_state["auth"]["role"] == "OPERATOR"
    assert any("Saha Operasyon Paneli" in title.value for title in app.title)
