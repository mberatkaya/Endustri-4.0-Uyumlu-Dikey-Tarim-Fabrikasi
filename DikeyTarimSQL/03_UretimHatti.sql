USE DikeyTarimDB;
GO

CREATE TABLE UretimHatti (
    HatID INT IDENTITY(1,1) PRIMARY KEY,
    HatAdi NVARCHAR(50) NOT NULL,
    Aciklama NVARCHAR(200)
);
GO

INSERT INTO UretimHatti (HatAdi, Aciklama) VALUES
('Hat A','Marul Uretim Hatti'),
('Hat B','Marul Uretim Hatti'),
('Hat C','Marul Uretim Hatti');
GO
