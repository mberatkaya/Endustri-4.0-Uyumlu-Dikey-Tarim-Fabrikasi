USE DikeyTarimDB;
GO

CREATE VIEW vw_AktifMarulPartileri AS
SELECT mp.PartiID, mp.KonumKodu, mp.PartiAdi, uh.HatAdi, mp.EkimTarihi,
DATEDIFF(DAY, mp.EkimTarihi, GETDATE()) + 1 AS KacinciGun,
mp.Cesit, mp.Durum
FROM MarulParti mp
INNER JOIN UretimHatti uh ON mp.HatID = uh.HatID
WHERE mp.Durum = 'Aktif';
GO

CREATE VIEW vw_SonSensorDegerleri AS
WITH SiraliSensorVerileri AS (
    SELECT sv.*,
    ROW_NUMBER() OVER (
        PARTITION BY sv.PartiID, sv.SensorTipi
        ORDER BY sv.TarihSaat DESC, sv.SensorVeriID DESC
    ) AS Sira
    FROM SensorVerileri sv
)
SELECT sv.SensorVeriID, mp.KonumKodu, mp.PartiAdi, sv.TarihSaat,
sv.SensorTipi, sv.Deger, sv.TDSDegeri, sv.Birim, sv.EvreAdi,
sv.EvreKodu, sv.GelisimGunu, sv.Alarm
FROM SiraliSensorVerileri sv
INNER JOIN MarulParti mp ON sv.PartiID = mp.PartiID
WHERE sv.Sira = 1;
GO

CREATE VIEW vw_OperatorGozlemListesi AS
SELECT og.GozlemID, mp.PartiAdi, k.AdSoyad AS OperatorAdi, og.GozlemTarihi, og.SorunTipi, og.Aciklama
FROM OperatorGozlemleri og
INNER JOIN MarulParti mp ON og.PartiID = mp.PartiID
INNER JOIN Kullanici k ON og.KullaniciID = k.KullaniciID;
GO
