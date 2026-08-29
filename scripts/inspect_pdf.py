import argparse
from pathlib import Path

from rti_extractor.pdf.reader import inspect, render_pages, sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect RTI PDFs.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--render", action="store_true", help="also write page PNGs")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    for path in sorted(args.paths):
        if not path.is_file():
            print(f"skip (not a file): {path}")
            continue

        info = inspect(path)
        chars = sum(len(text) for text in info.text_by_page)

        print(path.name[:60])
        print(
            f"   pages={info.page_count:<3} verdict={info.text_layer.value:<7}"
            f" chars={chars:<6} rotation={info.rotation_by_page}"
        )
        print(f"   sha256={sha256_file(path)[:16]}…  needs_images={info.needs_images}")

        if args.render:
            out_dir = Path("data/work") / path.stem[:40]
            written = render_pages(path, out_dir, dpi=args.dpi)
            print(f"   rendered {len(written)} page(s) → {out_dir}")


if __name__ == "__main__":
    main()
