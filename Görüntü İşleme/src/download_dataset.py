from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://zenodo.org/records/17719108/files/plantseg.zip?download=1"
DEFAULT_MD5 = "9358a66dff88cdd15c4fe009763c40a3"
DEFAULT_ZIP_PATH = ROOT / "data" / "raw" / "plantseg.zip"
DEFAULT_EXTRACT_DIR = ROOT / "data" / "plantseg"
SPLITS = ("train", "val", "test")
REPORT_STEP_BYTES = 256 * 1024 * 1024


def file_md5(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_suffix(target.suffix + ".download")
    if temp_path.exists():
        temp_path.unlink()

    request = urllib.request.Request(url, headers={"User-Agent": "plantseg-yolo-downloader"})
    with urllib.request.urlopen(request, timeout=120) as response, temp_path.open("wb") as handle:
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

    temp_path.replace(target)


def is_plantseg_root(path: Path) -> bool:
    return all(
        (path / "images" / split).is_dir() and (path / "annotations" / split).is_dir()
        for split in SPLITS
    )


def find_plantseg_root(extract_dir: Path) -> Path:
    if is_plantseg_root(extract_dir):
        return extract_dir

    for path in sorted(p for p in extract_dir.rglob("*") if p.is_dir()):
        if is_plantseg_root(path):
            return path

    raise FileNotFoundError(
        "PlantSeg kok klasoru bulunamadi: images/train ve annotations/train bekleniyor."
    )


def ensure_safe_delete(path: Path) -> None:
    resolved_path = path.resolve()
    resolved_root = ROOT.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise RuntimeError(f"Proje disindaki klasor silinmez: {path}")
    shutil.rmtree(path)


def safe_extract_zip(zip_path: Path, target_dir: Path, overwrite: bool) -> Path:
    if target_dir.exists():
        try:
            plantseg_root = find_plantseg_root(target_dir)
            if not overwrite:
                print(f"Mevcut PlantSeg klasoru kullaniliyor: {plantseg_root}")
                return plantseg_root
        except FileNotFoundError:
            if not overwrite:
                raise FileNotFoundError(
                    f"Eksik cikarma klasoru bulundu: {target_dir}\n"
                    "Yeniden cikarmak icin --overwrite ekle."
                )

        ensure_safe_delete(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    resolved_target = target_dir.resolve()

    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        print(f"Zip aciliyor: {len(members)} dosya -> {target_dir}")
        for index, member in enumerate(members, start=1):
            member_target = (target_dir / member.filename).resolve()
            if not member_target.is_relative_to(resolved_target):
                raise RuntimeError(f"Guvenli olmayan zip yolu: {member.filename}")
            archive.extract(member, target_dir)
            if index % 3000 == 0:
                print(f"Acildi: {index}/{len(members)}", flush=True)

    return find_plantseg_root(target_dir)


def print_split_counts(plantseg_root: Path) -> None:
    for split in SPLITS:
        image_count = len([p for p in (plantseg_root / "images" / split).iterdir() if p.is_file()])
        mask_count = len(
            [p for p in (plantseg_root / "annotations" / split).iterdir() if p.is_file()]
        )
        print(f"{split}: images={image_count}, annotations={mask_count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PlantSeg veri setini indir, dogrula ve cikar.")
    parser.add_argument("--url", default=DEFAULT_URL, help="PlantSeg zip indirme adresi.")
    parser.add_argument(
        "--zip-path", type=Path, default=DEFAULT_ZIP_PATH, help="Zip dosyasinin kaydedilecegi yol."
    )
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=DEFAULT_EXTRACT_DIR,
        help="Zip dosyasinin acilacagi klasor.",
    )
    parser.add_argument(
        "--md5",
        default=DEFAULT_MD5,
        help="Beklenen MD5 degeri. Bos string verirsen kontrol atlanir.",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Mevcut zip/cikarma klasorunu yeniden olustur."
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Mevcut gecerli zip ve cikarma klasorlerini kullan.",
    )
    parser.add_argument(
        "--no-extract", action="store_true", help="Sadece zip indir ve MD5 kontrolu yap."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    zip_path = args.zip_path.resolve()
    extract_dir = args.extract_dir.resolve()

    if zip_path.exists() and not args.overwrite:
        print(f"Mevcut zip kullaniliyor: {zip_path} ({zip_path.stat().st_size / 1e9:.2f} GB)")
    else:
        if zip_path.exists():
            zip_path.unlink()
        print(f"PlantSeg indiriliyor: {args.url}")
        download_file(args.url, zip_path)

    if args.md5:
        current_md5 = file_md5(zip_path)
        if current_md5 != args.md5:
            raise RuntimeError(f"MD5 uyusmadi. Beklenen={args.md5}, gelen={current_md5}")
        print("MD5 kontrolu basarili.")

    if args.no_extract:
        print(f"Zip hazir: {zip_path}")
        return

    plantseg_root = safe_extract_zip(zip_path, extract_dir, overwrite=args.overwrite)
    print(f"PlantSeg hazir: {plantseg_root}")
    print_split_counts(plantseg_root)


if __name__ == "__main__":
    main()
