import argparse
from pathlib import Path

from generate_epub import generate_cover_image, parse_cover_colors_arg


def main():
    parser = argparse.ArgumentParser(
        description="Генерирует отдельную обложку как JPEG на основе шаблонного стиля."
    )
    parser.add_argument("--title", required=True, help="Название книги")
    parser.add_argument("--author", default="", help="Имя автора")
    parser.add_argument("--width", type=int, default=1200, help="Ширина обложки (px)")
    parser.add_argument("--height", type=int, default=1600, help="Высота обложки (px)")
    parser.add_argument(
        "--cover-colors",
        default="",
        help="Пять HEX-цветов (полоска, верхний блок, заголовок, градиент начало, градиент конец)",
    )
    parser.add_argument(
        "--out",
        default="cover.jpg",
        help="Путь куда сохранить готовую обложку (JPEG).",
    )
    args = parser.parse_args()

    cover_colors = None
    if args.cover_colors:
        try:
            cover_colors = parse_cover_colors_arg(args.cover_colors)
        except ValueError as exc:
            parser.error(str(exc))

    cover_bytes = generate_cover_image(
        args.title,
        author=args.author,
        width=args.width,
        height=args.height,
        cover_colors=cover_colors,
    )
    Path(args.out).write_bytes(cover_bytes)
    print(f"Обложка сохранена: {args.out}")


if __name__ == "__main__":
    main()

