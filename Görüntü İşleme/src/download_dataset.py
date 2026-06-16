import hashlib
import urllib.request
import zipfile
from pathlib import Path



# AYARLAR


ROOT = Path(__file__).resolve().parents[1]

URL = "https://zenodo.org/records/17719108/files/plantseg.zip?download=1"  # Zenodo indirme adresi.
MD5 = "9358a66dff88cdd15c4fe009763c40a3"                                   # Beklenen MD5 (indirme dogrulamasi).
ZIP_PATH = ROOT / "data" / "raw" / "plantseg.zip"                          # Indirilen zip'in kaydedilecegi yer.
EXTRACT_DIR = ROOT / "data" / "plantseg"                                   # Zip'in acilacagi klasor.

SPLITS = ("train", "val", "test")
REPORT_STEP_BYTES = 256 * 1024 * 1024  # Her 256 MB'da bir ilerleme yazdırılıyor


def file_md5(path: Path) -> str:
    """Dosyanin MD5 ozetini hesaplar.
    """
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, target: Path) -> None:
    """Dosyayi indirir ve ilerlemeyi yazdirir.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "plantseg-yolo-downloader"})

    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        next_report = REPORT_STEP_BYTES

        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if downloaded >= next_report:
                if total:
                    print(f"Indirildi: {downloaded / 1e9:.2f}/{total / 1e9:.2f} GB", flush=True)
                else:
                    print(f"Indirildi: {downloaded / 1e9:.2f} GB", flush=True)
                next_report += REPORT_STEP_BYTES


def is_plantseg_root(path: Path) -> bool:
    """Bir klasorun PlantSeg kok klasoru olup olmadigini kontrol eder.

    Kok klasorde her split icin hem images/<split> hem annotations/<split>
    alt klasorleri bulunmalidir.
    """
    return all(
        (path / "images" / split).is_dir() and (path / "annotations" / split).is_dir()
        for split in SPLITS
    )


def find_plantseg_root(extract_dir: Path) -> Path:
    """Cikartilan klasor icinde gercek PlantSeg kokunu bulur.

    Zip bazen dosyalari bir ust klasorun icine acar (orn. plantseg/plantseg/...).
    Bu yuzden once klasorun kendisine, sonra tum alt klasorlere bakip
    images/annotations yapisina sahip olani buluruz.
    """
    if is_plantseg_root(extract_dir):
        return extract_dir
    for path in sorted(p for p in extract_dir.rglob("*") if p.is_dir()):
        if is_plantseg_root(path):
            return path
    raise FileNotFoundError("PlantSeg kok klasoru bulunamadi: images/train ve annotations/train bekleniyor.")


def extract_zip(zip_path: Path, target_dir: Path) -> Path:
    """Zip dosyasini acar ve PlantSeg kok klasorunu dondurur.

    Eger hedef klasor zaten gecerli bir PlantSeg yapisi iceriyorsa tekrar acmaz,
    mevcut klasoru kullanir.
    """
    if target_dir.exists():
        try:
            plantseg_root = find_plantseg_root(target_dir)
            print(f"Mevcut PlantSeg klasoru kullaniliyor: {plantseg_root}")
            return plantseg_root
        except FileNotFoundError:
            pass  # Eksik/yarim cikma; asagida yeniden aciyoruz.

    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        print(f"Zip aciliyor: {len(archive.infolist())} dosya -> {target_dir}")
        archive.extractall(target_dir)  # Guvenilir Zenodo zip'i; dogrudan aciyoruz.

    return find_plantseg_root(target_dir)


def print_split_counts(plantseg_root: Path) -> None:
    """Her split icin kac goruntu ve kac maske oldugunu yazdirir."""
    for split in SPLITS:
        image_count = len([p for p in (plantseg_root / "images" / split).iterdir() if p.is_file()])
        mask_count = len([p for p in (plantseg_root / "annotations" / split).iterdir() if p.is_file()])
        print(f"{split}: images={image_count}, annotations={mask_count}")


def main() -> None:
    zip_path = ZIP_PATH.resolve()
    extract_dir = EXTRACT_DIR.resolve()

    # 1) Zip yoksa indir varsa tekrar indirmeyip mevcut dosyayi kullan.
    if zip_path.exists():
        print(f"Mevcut zip kullaniliyor: {zip_path} ({zip_path.stat().st_size / 1e9:.2f} GB)")
    else:
        print(f"PlantSeg indiriliyor: {URL}")
        download_file(URL, zip_path)

    # 2) Indirilen dosya bozulmamis mi diye MD5 kontrolu yap.
    current_md5 = file_md5(zip_path)
    if current_md5 != MD5:
        raise RuntimeError(f"MD5 uyusmadi. Beklenen={MD5}, gelen={current_md5}")
    print("MD5 kontrolu basarili.")

    # 3) Zip'i ac ve sonucu ozetle.
    plantseg_root = extract_zip(zip_path, extract_dir)
    print(f"PlantSeg hazir: {plantseg_root}")
    print_split_counts(plantseg_root)


if __name__ == "__main__":
    main()
