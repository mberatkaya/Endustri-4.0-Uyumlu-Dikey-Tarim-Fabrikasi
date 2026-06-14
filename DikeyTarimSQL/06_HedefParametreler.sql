USE DikeyTarimDB;
GO

CREATE TABLE HedefParametreler (
    ParametreID INT IDENTITY(1,1) PRIMARY KEY,
    EvreID INT NOT NULL UNIQUE,
    MinPH DECIMAL(4,2), MaxPH DECIMAL(4,2),
    MinEC DECIMAL(4,2), MaxEC DECIMAL(4,2),
    MinNem DECIMAL(5,2), MaxNem DECIMAL(5,2),
    MinSicaklik DECIMAL(5,2), MaxSicaklik DECIMAL(5,2),
    MinCO2 DECIMAL(8,2), MaxCO2 DECIMAL(8,2),
    MinIsik DECIMAL(8,2), MaxIsik DECIMAL(8,2),
    Risk NVARCHAR(200),
    Mudahale NVARCHAR(300),
    CONSTRAINT FK_HedefParametreler_Evre FOREIGN KEY (EvreID) REFERENCES GelisimEvreleri(EvreID)
);
GO

INSERT INTO HedefParametreler (
    EvreID, MinPH, MaxPH, MinEC, MaxEC, MinNem, MaxNem,
    MinSicaklik, MaxSicaklik, MinCO2, MaxCO2, MinIsik, MaxIsik, Risk, Mudahale
) VALUES
(1,5.5,5.8,0.5,0.8,80,90,20,23,350,420,80,120,
 'Dusuk isik zayif cikisa yol acabilir','Isik, nem ve sicaklik kontrol edilmeli'),
(2,5.8,6.0,1.0,1.2,70,75,20,22,550,650,150,180,
 'Yuksek nem fungal riski artirabilir','Nem ve besin cozeltileri kontrol edilmeli'),
(3,5.8,6.2,1.2,1.4,65,70,19,22,750,850,200,250,
 'pH sapmasi besin alimini bozabilir','pH ve EC dengesi kontrol edilmeli'),
(4,5.7,6.1,1.5,1.8,60,65,18,21,950,1050,250,300,
 'Dusuk CO2 fotosentezi azaltabilir','CO2 ve hava sirkulasyonu kontrol edilmeli'),
(5,5.6,6.0,1.8,2.0,60,65,18,22,950,1050,290,310,
 'Yuksek sicaklik acilasmaya yol acabilir','Sicaklik ve isik suresi kontrol edilmeli'),
(6,5.8,6.2,1.2,1.4,55,60,17,20,370,430,190,210,
 'Tuz birikimi hasat kalitesini dusurebilir','EC dusurulmeli veya sistem flush edilmelidir');
GO
