USE DikeyTarimDB;
GO

CREATE TABLE OperatorGozlemleri (
    GozlemID INT IDENTITY(1,1) PRIMARY KEY,
    PartiID INT NOT NULL,
    KullaniciID INT NOT NULL,
    GozlemTarihi DATETIME NOT NULL,
    SorunTipi NVARCHAR(100),
    Aciklama NVARCHAR(500),
    CONSTRAINT FK_OperatorGozlemleri_MarulParti FOREIGN KEY (PartiID) REFERENCES MarulParti(PartiID),
    CONSTRAINT FK_OperatorGozlemleri_Kullanici FOREIGN KEY (KullaniciID) REFERENCES Kullanici(KullaniciID)
);
GO

INSERT INTO OperatorGozlemleri (PartiID,KullaniciID,GozlemTarihi,SorunTipi,Aciklama) VALUES
(1,2,GETDATE(),'Yaprak Sararmasi','Sensor degerleri normal ancak yapraklarda sararma basladi'),
(2,2,GETDATE(),'Deformasyon','Yaprak kenarlarinda deformasyon gozlemlendi');
GO
