import argparse
from pathlib import Path

from rti_extractor.extract.client import extract_from_images, extract_from_text
from rti_extractor.logging import setup_logging
from rti_extractor.pdf.reader import TextLayer, inspect, render_pages
from rti_extractor.rti_type import get_rti_type


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Budget RTI answers from a PDF.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    setup_logging()
    rti_type = get_rti_type("budget-rti")

    info = inspect(args.path)
    print(args.path.name)
    print(f"  pages={info.page_count}  verdict={info.text_layer.value}\n")

    if info.text_layer is TextLayer.NATIVE:
        answers = extract_from_text(rti_type, "\n\n".join(info.text_by_page))
    else:
        out_dir = Path("data/work") / args.path.stem[:40]
        pages = render_pages(args.path, out_dir, dpi=args.dpi)
        print(f"  rendered {len(pages)} page(s) at {args.dpi} dpi\n")
        answers = extract_from_images(rti_type, pages)

    print(answers.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
