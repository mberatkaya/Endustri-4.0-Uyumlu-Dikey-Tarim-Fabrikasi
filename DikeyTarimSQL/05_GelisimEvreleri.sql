USE DikeyTarimDB;
GO

CREATE TABLE GelisimEvreleri (
    EvreID INT IDENTITY(1,1) PRIMARY KEY,
    EvreKodu NVARCHAR(10) NOT NULL UNIQUE,
    EvreAdi NVARCHAR(50) NOT NULL,
    BaslangicGun INT NOT NULL,
    BitisGun INT NOT NULL,
    CONSTRAINT CK_GelisimEvreleri_GunAraligi CHECK (BaslangicGun <= BitisGun)
);
GO

INSERT INTO GelisimEvreleri (EvreKodu, EvreAdi, BaslangicGun, BitisGun) VALUES
('E2','Cimlenme',1,3),
('E3','Fide Baslangic',4,10),
('E4','Fide Gelisim',11,15),
('E5','NFT Adaptasyon',16,25),
('E6','Hizli Buyume',26,35),
('E7','Hasat Oncesi',36,40);
GO
