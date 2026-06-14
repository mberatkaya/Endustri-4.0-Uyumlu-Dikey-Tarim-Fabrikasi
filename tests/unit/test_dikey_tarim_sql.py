from __future__ import annotations

import re
from pathlib import Path

SQL_ROOT = Path(__file__).resolve().parents[2] / "DikeyTarimSQL"


def read_sql(filename: str) -> str:
    return (SQL_ROOT / filename).read_text(encoding="utf-8")


def test_sql_scripts_have_deterministic_execution_order():
    assert [path.name for path in sorted(SQL_ROOT.glob("*.sql"))] == [
        "01_Veritabani.sql",
        "02_Kullanici.sql",
        "03_UretimHatti.sql",
        "04_MarulParti.sql",
        "05_GelisimEvreleri.sql",
        "06_HedefParametreler.sql",
        "07_SensorVerileri.sql",
        "08_OperatorGozlemleri.sql",
        "09_UyariKayitlari.sql",
        "10_Viewlar.sql",
        "11_StoredProcedures.sql",
        "12_Trigger.sql",
        "13_RaporSorgulari.sql",
        "14_TumCiktilariGoster.sql",
    ]


def test_batch_schema_maps_unique_location_code():
    sql = read_sql("04_MarulParti.sql")

    assert "KonumKodu NVARCHAR(20) NOT NULL UNIQUE" in sql
    assert all(code in sql for code in ("Z1-F1", "Z2-F1", "Z3-F1"))


def test_growth_stage_and_target_seed_cover_six_simulator_stages():
    stages_sql = read_sql("05_GelisimEvreleri.sql")
    targets_sql = read_sql("06_HedefParametreler.sql")

    assert re.findall(r"\('E[2-7]'", stages_sql) == [
        "('E2'",
        "('E3'",
        "('E4'",
        "('E5'",
        "('E6'",
        "('E7'",
    ]
    assert len(re.findall(r"^\([1-6],", targets_sql, flags=re.MULTILINE)) == 6
    assert all(column in targets_sql for column in ("MinCO2", "MaxCO2", "MinIsik", "MaxIsik"))


def test_sensor_schema_is_normalized_for_single_mqtt_measurements():
    sql = read_sql("07_SensorVerileri.sql")

    assert all(
        column in sql
        for column in (
            "SensorTipi NVARCHAR(30) NOT NULL",
            "Deger DECIMAL(10,2) NOT NULL",
            "TDSDegeri DECIMAL(10,2)",
            "EvreKodu NVARCHAR(10) NOT NULL",
            "GelisimGunu INT NOT NULL",
            "Alarm BIT NOT NULL",
        )
    )
    assert "PH DECIMAL" not in sql
    assert "EC DECIMAL" not in sql


def test_sensor_procedure_resolves_active_batch_by_location():
    sql = read_sql("11_StoredProcedures.sql")

    assert "CREATE PROCEDURE dbo.sp_SensorVerisiEkle" in sql
    assert "@KonumKodu NVARCHAR(20)" in sql
    assert "WHERE KonumKodu = @KonumKodu AND Durum = 'Aktif'" in sql
    assert "THROW 50001" in sql
    assert "INSERT INTO SensorVerileri" in sql


def test_alarm_trigger_uses_payload_alarm_flag():
    sql = read_sql("12_Trigger.sql")

    assert "CREATE TRIGGER dbo.trg_Sensor_Uyari" in sql
    assert "WHERE i.Alarm = 1" in sql
    assert "INSERT INTO UyariKayitlari" in sql


def test_latest_sensor_view_partitions_by_batch_and_sensor():
    sql = read_sql("10_Viewlar.sql")

    assert "PARTITION BY sv.PartiID, sv.SensorTipi" in sql
    assert "WHERE sv.Sira = 1" in sql
