USE DikeyTarimDB;
GO

CREATE PROCEDURE dbo.sp_SensorVerisiEkle
    @KonumKodu NVARCHAR(20),
    @TarihSaat DATETIME2(3),
    @SensorTipi NVARCHAR(30),
    @Deger DECIMAL(10,2),
    @TDSDegeri DECIMAL(10,2),
    @Birim NVARCHAR(20),
    @EvreAdi NVARCHAR(50),
    @EvreKodu NVARCHAR(10),
    @GelisimGunu INT,
    @Alarm BIT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @PartiID INT;
    SELECT @PartiID = PartiID
    FROM MarulParti
    WHERE KonumKodu = @KonumKodu AND Durum = 'Aktif';

    IF @PartiID IS NULL
        THROW 50001, 'Konum kodu icin aktif marul partisi bulunamadi.', 1;

    INSERT INTO SensorVerileri (
        PartiID, TarihSaat, SensorTipi, Deger, TDSDegeri, Birim,
        EvreAdi, EvreKodu, GelisimGunu, Alarm
    )
    VALUES (
        @PartiID, @TarihSaat, @SensorTipi, @Deger, @TDSDegeri, @Birim,
        @EvreAdi, @EvreKodu, @GelisimGunu, @Alarm
    );
END;
GO

CREATE PROCEDURE dbo.sp_OperatorGozlemEkle
    @PartiID INT, @KullaniciID INT, @SorunTipi NVARCHAR(100), @Aciklama NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO OperatorGozlemleri (PartiID,KullaniciID,GozlemTarihi,SorunTipi,Aciklama)
    VALUES (@PartiID,@KullaniciID,GETDATE(),@SorunTipi,@Aciklama);
END;
GO
