USE DikeyTarimDB;
GO

CREATE TABLE SensorVerileri (
    SensorVeriID INT IDENTITY(1,1) PRIMARY KEY,
    PartiID INT NOT NULL,
    TarihSaat DATETIME2(3) NOT NULL,
    SensorTipi NVARCHAR(30) NOT NULL,
    Deger DECIMAL(10,2) NOT NULL,
    TDSDegeri DECIMAL(10,2),
    Birim NVARCHAR(20),
    EvreAdi NVARCHAR(50) NOT NULL,
    EvreKodu NVARCHAR(10) NOT NULL,
    GelisimGunu INT NOT NULL,
    Alarm BIT NOT NULL CONSTRAINT DF_SensorVerileri_Alarm DEFAULT 0,
    CONSTRAINT CK_SensorVerileri_SensorTipi CHECK (
        SensorTipi IN ('ph','ec','temperature','humidity','co2','light')
    ),
    CONSTRAINT FK_SensorVerileri_MarulParti FOREIGN KEY (PartiID) REFERENCES MarulParti(PartiID)
);
GO

CREATE INDEX IX_SensorVerileri_Parti_Sensor_Tarih
ON SensorVerileri (PartiID, SensorTipi, TarihSaat DESC);
GO

INSERT INTO SensorVerileri (
    PartiID, TarihSaat, SensorTipi, Deger, TDSDegeri, Birim,
    EvreAdi, EvreKodu, GelisimGunu, Alarm
) VALUES
(1,'2026-06-02 08:00','ph',5.60,NULL,'pH','Cimlenme','E2',2,0),
(1,'2026-06-02 08:00','ec',0.60,384.00,'mS/cm','Cimlenme','E2',2,0),
(2,'2026-06-06 08:00','humidity',72.00,NULL,'%','Fide Baslangic','E3',4,0),
(3,'2026-06-10 08:00','light',300.00,NULL,'umol','NFT Adaptasyon','E5',17,0);
GO
