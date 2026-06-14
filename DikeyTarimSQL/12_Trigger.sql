USE DikeyTarimDB;
GO

CREATE TRIGGER dbo.trg_Sensor_Uyari
ON SensorVerileri
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO UyariKayitlari (PartiID,SensorVeriID,UyariTarihi,UyariTipi,Aciklama)
    SELECT i.PartiID, i.SensorVeriID, i.TarihSaat,
    CONCAT(i.SensorTipi, ' Uyarisi'),
    CONCAT(i.SensorTipi, ' sensor degeri alarm esiginin disindadir. Deger: ', i.Deger)
    FROM inserted i
    WHERE i.Alarm = 1;
END;
GO
