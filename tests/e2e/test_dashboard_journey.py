from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_operator_sensor_prediction_dashboard_flow(page: Page):
    page.goto("http://127.0.0.1:8501")
    page.get_by_label("Kullanıcı Adı").fill("operator")
    page.get_by_label("Şifre").fill("123")
    page.get_by_role("button", name="Giriş Yap").click()

    expect(page.get_by_text("Saha Operasyon Paneli")).to_be_visible()
    page.get_by_text("Genel İşlemler", exact=True).click()
    page.get_by_label("Üretim Tanımı (Operatör Açıklaması)").fill("CI Marul")
    page.get_by_role("button", name="Süreci Tetikle").click()

    page.get_by_text("Hat İzleme", exact=True).click()
    expect(page.get_by_text("CI Marul", exact=True)).to_be_visible()
    expect(page.get_by_text("hasadına tahmini", exact=False)).to_be_visible()
