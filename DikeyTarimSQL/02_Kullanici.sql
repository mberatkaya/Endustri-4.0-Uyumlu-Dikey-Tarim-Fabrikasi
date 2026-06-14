USE DikeyTarimDB;
GO

CREATE TABLE Kullanici (
    KullaniciID INT IDENTITY(1,1) PRIMARY KEY,
    AdSoyad NVARCHAR(100) NOT NULL,
    KullaniciAdi NVARCHAR(50) NOT NULL UNIQUE,
    Sifre NVARCHAR(100) NOT NULL,
    Rol NVARCHAR(20) NOT NULL
);
GO

INSERT INTO Kullanici (AdSoyad, KullaniciAdi, Sifre, Rol) VALUES
('Muhammet Mert Arslan','mert','12345','Yonetici'),
('Ahmet Yilmaz','ahmet','12345','Operator');
GO
