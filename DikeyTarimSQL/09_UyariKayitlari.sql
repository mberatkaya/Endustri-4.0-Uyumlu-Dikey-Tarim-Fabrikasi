USE DikeyTarimDB;
GO

CREATE TABLE UyariKayitlari (
    UyariID INT IDENTITY(1,1) PRIMARY KEY,
    PartiID INT NOT NULL,
    SensorVeriID INT NOT NULL UNIQUE,
    UyariTarihi DATETIME2(3) NOT NULL,
    UyariTipi NVARCHAR(100),
    Aciklama NVARCHAR(500),
    CONSTRAINT FK_UyariKayitlari_MarulParti FOREIGN KEY (PartiID) REFERENCES MarulParti(PartiID),
    CONSTRAINT FK_UyariKayitlari_SensorVerileri FOREIGN KEY (SensorVeriID) REFERENCES SensorVerileri(SensorVeriID)
);
GO
