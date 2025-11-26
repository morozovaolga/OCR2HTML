import argparse
import json
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from html import escape as hesc
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def load_blocks_from_json(json_path: Path):
    """Загрузить блоки из JSON файла (structured.json или structured_rules.json)"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return data.get("blocks", [])


def looks_like_section_heading(line: str) -> bool:
    """Проверить, начинается ли строка с признака заголовка (Часть/Глава/Раздел/Книга, римское число, ***)."""
    if not line:
        return False
    stripped = line.strip()
    if not stripped:
        return False

    keyword_pattern = re.compile(r'^(?:Часть|Глава|Раздел|Книга)\b.*\d', re.IGNORECASE)
    if keyword_pattern.match(stripped):
        return True

    if re.match(r'^[IVXLCDM]+\b', stripped, re.IGNORECASE):
        return True

    if re.match(r'^\*\s*\*\s*\*', stripped):
        return True

    return False


def paragraphs_to_blocks(paragraphs):
    """Преобразовать список абзацев в блоки (heading/paragraph)"""
    blocks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = [line.strip() for line in para.splitlines() if line.strip()]
        if not lines:
            continue

        first_line = lines[0]
        is_heading = (
            (len(first_line) < 100 and
             (
                 first_line.isupper() or
                 (len(lines) == 1 and len(first_line) < 50)
             ) and
             not first_line.endswith(('.', ',', ';', ':', '!', '?')))
            or looks_like_section_heading(first_line)
        )

        para_text = ' '.join(lines).strip()
        para_text = re.sub(r'\s+', ' ', para_text)

        if para_text:
            blocks.append({
                "role": "heading" if is_heading else "paragraph",
                "text": para_text
            })
    return blocks


def load_blocks_from_html(html_path: Path):
    """Загрузить блоки из HTML файла (парсит h2, p и pre теги)"""
    html = html_path.read_text(encoding="utf-8")
    blocks = []
    
    # Сначала пробуем найти h2 и p теги (формат modernize_structured.py)
    h2_pattern = r'<h2[^>]*>(.*?)</h2>'
    p_pattern = r'<p[^>]*>(.*?)</p>'
    pre_pattern = r'<pre[^>]*>(.*?)</pre>'
    
    # Проверяем, есть ли pre тег (формат lt_cloud.py)
    pre_match = re.search(pre_pattern, html, re.DOTALL | re.IGNORECASE)
    
    if pre_match:
        pre_content = pre_match.group(1)
        # Декодируем HTML entities
        pre_content = pre_content.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        # Убираем HTML теги, если есть
        pre_content = re.sub(r'<[^>]+>', '', pre_content)
        
        paragraphs = re.split(r'\n\s*\n', pre_content)
        blocks.extend(paragraphs_to_blocks(paragraphs))
    else:
        pos = 0
        while pos < len(html):
            h2_match = re.search(h2_pattern, html[pos:], re.DOTALL | re.IGNORECASE)
            p_match = re.search(p_pattern, html[pos:], re.DOTALL | re.IGNORECASE)
            
            if h2_match and (not p_match or h2_match.start() < p_match.start()):
                text = h2_match.group(1)
                text = re.sub(r'<mark[^>]*>(.*?)</mark>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', '', text)
                text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    blocks.append({"role": "heading", "text": text})
                pos += h2_match.end()
            elif p_match:
                text = p_match.group(1)
                text = re.sub(r'<mark[^>]*>(.*?)</mark>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', '', text)
                text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    blocks.append({"role": "paragraph", "text": text})
                pos += p_match.end()
            else:
                break
    
    return blocks


def load_blocks_from_text(text: str):
    """Загрузить блоки из plain text файла (final_clean.txt или final.txt)"""
    paragraphs = re.split(r'\n\s*\n', text)
    if len(paragraphs) <= 1 and '\n' in text:
        paragraphs = text.splitlines()
    return paragraphs_to_blocks(paragraphs)


def split_into_chapters(blocks, max_size_kb=50):
    """Разбить блоки по главах (заголовки) и по размеру, если заголовков нет."""
    chapters = []
    current_blocks = []
    current_title = None
    current_size = 0
    chapter_index = 1
    max_size = max_size_kb * 1024

    def flush():
        nonlocal current_blocks, current_title, current_size, chapter_index
        if not current_blocks:
            return
        title = current_title or f"Глава {chapter_index}"
        chapters.append({"title": title, "blocks": current_blocks})
        chapter_index += 1
        current_blocks = []
        current_title = None
        current_size = 0

    for block in blocks:
        text = block.get("text", "").strip()
        block_size = len(text.encode("utf-8"))
        role = block.get("role")

        if role == "heading":
            if current_blocks:
                flush()
            current_title = text or f"Глава {chapter_index}"
            current_blocks.append(block)
            current_size = block_size
            continue

        if current_blocks and current_size + block_size > max_size:
            flush()

        if not current_blocks:
            current_title = f"Глава {chapter_index}"

        current_blocks.append(block)
        current_size += block_size

    flush()
    return chapters


def generate_cover_image(title: str, author: str = "", prompt: str = "", width: int = 1200, height: int = 1600) -> bytes:
    """Генерировать изображение обложки с названием и автором"""
    if not HAS_PIL:
        raise ImportError("Pillow (PIL) не установлен. Установите: pip install Pillow")

    import random
    import colorsys
    import math

    rand = random.Random()
    palette = []
    for _ in range(3):
        hue = rand.random()
        sat = rand.uniform(0.4, 0.82)
        val = rand.uniform(0.35, 0.9)
        rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, sat, val))
        palette.append((val, rgb))

    palette.sort(key=lambda item: item[0])
    color_a = palette[0][1]
    color_b = palette[1][1]
    color_c = palette[2][1]

    orientation = rand.choice(["vertical", "horizontal", "diagonal", "radial"])
    img = Image.new("RGB", (width, height), color=color_a)
    for y in range(height):
        for x in range(width):
            if orientation == "vertical":
                ratio = y / max(1, height - 1)
            elif orientation == "horizontal":
                ratio = x / max(1, width - 1)
            elif orientation == "diagonal":
                ratio = (x + y) / max(1, width + height - 2)
            else:  # radial
                cx = width / 2
                cy = height / 2
                dist = math.hypot(x - cx, y - cy)
                max_dist = math.hypot(cx, cy)
                ratio = dist / max_dist

            if ratio < 0.5:
                local_ratio = ratio * 2
                r = int(color_a[0] + (color_b[0] - color_a[0]) * local_ratio)
                g = int(color_a[1] + (color_b[1] - color_a[1]) * local_ratio)
                b = int(color_a[2] + (color_b[2] - color_a[2]) * local_ratio)
            else:
                local_ratio = (ratio - 0.5) * 2
                r = int(color_b[0] + (color_c[0] - color_b[0]) * local_ratio)
                g = int(color_b[1] + (color_c[1] - color_b[1]) * local_ratio)
                b = int(color_b[2] + (color_c[2] - color_b[2]) * local_ratio)

            img.putpixel((x, y), (r, g, b))

    # Добавляем полупрозрачные паттерны по поверхности
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pattern_draw = ImageDraw.Draw(overlay)
    for _ in range(rand.randint(2, 4)):
        shape_color = tuple(min(255, c + 50) for c in color_c) + (rand.randint(30, 70),)
        shape_type = rand.choice(["circle", "stripe"])
        if shape_type == "circle":
            radius = rand.randint(width // 5, width // 2)
            cx = rand.randint(0, width)
            cy = rand.randint(0, height)
            pattern_draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=shape_color)
        else:
            thickness = rand.randint(30, 70)
            if rand.choice([True, False]):
                pattern_draw.rectangle([0, rand.randint(0, height), width, rand.randint(0, height) + thickness],
                                       fill=shape_color)
            else:
                pattern_draw.rectangle([rand.randint(0, width), 0, rand.randint(0, width) + thickness, height],
                                       fill=shape_color)

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    # Пробуем загрузить шрифт, если не получается - используем стандартный
    try:
        # Пробуем найти системный шрифт
        title_font = ImageFont.truetype("arial.ttf", 72)
        author_font = ImageFont.truetype("arial.ttf", 48)
    except:
        try:
            # Альтернативные пути для Windows
            title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
            author_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
        except:
            # Используем стандартный шрифт
            title_font = ImageFont.load_default()
            author_font = ImageFont.load_default()
    
    # Разбиваем заголовок на строки, если он слишком длинный
    title_lines = []
    words = title.split()
    current_line = ""
    max_width = width - 200  # Отступы по 100px с каждой стороны
    
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=title_font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                title_lines.append(current_line)
            current_line = word
    
    if current_line:
        title_lines.append(current_line)
    
    draw = ImageDraw.Draw(img)
    # Рисуем заголовок
    title_y = height // 3
    line_height = 90
    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = title_y + i * line_height
        
        # Тень для текста (темно-серый)
        draw.text((x + 3, y + 3), line, font=title_font, fill=(50, 50, 50))
        # Основной текст
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255))
    
    # Рисуем автора, если указан
    if author:
        bbox = draw.textbbox((0, 0), author, font=author_font)
        text_width = bbox[2] - bbox[0]
        author_x = (width - text_width) // 2
        author_y = height - 300
        
        # Тень для текста (темно-серый)
        draw.text((author_x + 2, author_y + 2), author, font=author_font, fill=(50, 50, 50))
        # Основной текст
        draw.text((author_x, author_y), author, font=author_font, fill=(200, 200, 200))
    
    prompt = prompt.strip()
    if prompt:
        prompt_font = author_font
        prompt_y = height - 200
        prompt_text = f"Prompt: {prompt}"
        prompt_bbox = draw.textbbox((0, 0), prompt_text, font=prompt_font)
        prompt_width = prompt_bbox[2] - prompt_bbox[0]
        draw.text(((width - prompt_width) // 2, prompt_y), prompt_text, font=prompt_font, fill=(230, 230, 230))

    # Сохраняем в байты (JPEG)
    from io import BytesIO
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG', quality=90)
    return img_bytes.getvalue()


def create_xhtml_section(blocks, title, css_href="../Styles/Style0001.css"):
    """Создать XHTML файл для раздела"""
    body_parts = []
    for block in blocks:
        text = hesc(block.get("text", ""))
        if block.get("role") == "heading":
            body_parts.append(f"<h2>{text}</h2>")
        else:
            body_parts.append(f"<p>{text}</p>")
    
    xhtml = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>

<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
 <title>{hesc(title)}</title>
 <link href="{css_href}" rel="stylesheet" type="text/css"/>
</head>

<body>
{chr(10).join(body_parts)}
</body>
</html>'''
    
    return xhtml


def update_content_opf(opf_content: str, section_files: list, title: str, author: str = "", has_cover: bool = False, sections: list = None):
    """Обновить content.opf с новыми разделами"""
    # Парсим XML
    root = ET.fromstring(opf_content)
    
    # Определяем namespace из корневого элемента
    opf_ns = 'http://www.idpf.org/2007/opf'
    dc_ns = 'http://purl.org/dc/elements/1.1/'
    dcterms_ns = 'http://purl.org/dc/terms/'
    
    # Находим namespace префиксы из корневого элемента
    ns_map = {}
    if root.tag.startswith('{'):
        # Извлекаем namespace из тега
        ns_uri = root.tag[1:].split('}')[0]
        ns_map[''] = ns_uri
    
    # Используем полные namespace URI для поиска
    ns = {'opf': opf_ns, 'dc': dc_ns}
    
    # Обновляем заголовок
    title_elem = root.find(f'.//{{{dc_ns}}}title')
    if title_elem is not None:
        title_elem.text = title
    
    # Обновляем или добавляем автора
    if author:
        metadata = root.find(f'.//{{{opf_ns}}}metadata')
        if metadata is not None:
            # Ищем существующего автора
            creator_elem = metadata.find(f'.//{{{dc_ns}}}creator')
            if creator_elem is not None:
                creator_elem.text = author
            else:
                # Создаем нового автора
                creator = ET.SubElement(metadata, f'{{{dc_ns}}}creator')
                creator.set('id', 'cre')
                creator.text = author
                # Добавляем meta для роли
                meta_role = ET.SubElement(metadata, f'{{{opf_ns}}}meta')
                meta_role.set('refines', '#cre')
                meta_role.set('property', 'role')
                meta_role.set('scheme', 'marc:relators')
                meta_role.text = 'aut'
    
    # Обновляем дату модификации
    # Ищем meta с property="dcterms:modified"
    modified_elem = None
    for meta in root.findall(f'.//{{{opf_ns}}}meta'):
        if meta.get('property') == 'dcterms:modified':
            modified_elem = meta
            break
    
    if modified_elem is None:
        # Создаем новый meta элемент
        metadata = root.find(f'.//{{{opf_ns}}}metadata')
        if metadata is not None:
            meta = ET.SubElement(metadata, f'{{{opf_ns}}}meta')
            meta.set('property', 'dcterms:modified')
            modified_elem = meta
    
    if modified_elem is not None:
        modified_elem.set('content', datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    
    # Обновляем identifier (генерируем новый UUID)
    identifier = root.find(f'.//{{{dc_ns}}}identifier[@id="BookId"]')
    if identifier is not None:
        identifier.text = f'urn:uuid:{uuid.uuid4()}'
    
    # Обновляем обложку в manifest, если создана новая
    if has_cover:
        manifest = root.find(f'.//{{{opf_ns}}}manifest')
        if manifest is not None:
            # Удаляем старую обложку, если есть
            for item in list(manifest):
                href = item.get('href', '')
                if 'cover' in href.lower() and href.endswith(('.jpg', '.jpeg', '.png')):
                    manifest.remove(item)
            
            # Добавляем новую обложку
            cover_item = ET.SubElement(manifest, f'{{{opf_ns}}}item')
            cover_item.set('id', 'cover-image')
            cover_item.set('href', 'Images/cover.jpg')
            cover_item.set('media-type', 'image/jpeg')
            cover_item.set('properties', 'cover-image')
    
    # Находим manifest и spine
    manifest = root.find(f'.//{{{opf_ns}}}manifest')
    spine = root.find(f'.//{{{opf_ns}}}spine')
    
    if manifest is None or spine is None:
        return opf_content  # Не удалось найти, возвращаем как есть
    
    # Удаляем старые Section файлы из manifest и spine
    for item in list(manifest):
        href = item.get('href', '')
        if href.startswith('Text/Chapter') and href.endswith('.xhtml'):
            manifest.remove(item)
    
    for itemref in list(spine):
        idref = itemref.get('idref', '')
        if idref.startswith('Chapter'):
            spine.remove(itemref)
    
    # Находим позицию для вставки разделов (после последнего не-Section элемента)
    insert_pos = len(spine)
    for idx, itemref in enumerate(spine):
        idref = itemref.get('idref', '')
        if idref.startswith('Chapter'):
            insert_pos = idx
            break
    
    # Добавляем новые разделы в manifest и spine (в правильном порядке)
        for i, section_file in enumerate(section_files, 1):
            section_id = f"Chapter{i:04d}.xhtml"
            item_id = f"Chapter{i:04d}"
        href = f"Text/{section_id}"
        
        # Добавляем в manifest
        item = ET.SubElement(manifest, f'{{{opf_ns}}}item')
        item.set('id', item_id)
        item.set('href', href)
        item.set('media-type', 'application/xhtml+xml')
        
        # Добавляем в spine в правильном порядке (последовательно)
        itemref = ET.Element(f'{{{opf_ns}}}itemref')
        itemref.set('idref', item_id)
        spine.insert(insert_pos + i - 1, itemref)
    
    # Обновляем guide для обложки
    if has_cover:
        guide = root.find(f'.//{{{opf_ns}}}guide')
        if guide is None:
            guide = ET.SubElement(root, f'{{{opf_ns}}}guide')
        
        # Удаляем старую ссылку на обложку
        for ref in list(guide):
            if ref.get('type') == 'cover':
                guide.remove(ref)
        
        # Добавляем новую ссылку на обложку
        cover_ref = ET.SubElement(guide, f'{{{opf_ns}}}reference')
        cover_ref.set('type', 'cover')
        cover_ref.set('title', 'Обложка')
        cover_ref.set('href', 'Text/cover.xhtml')
    
    # Преобразуем обратно в строку
    # Сохраняем исходные namespace префиксы
    ET.register_namespace('', opf_ns)
    ET.register_namespace('dc', dc_ns)
    ET.register_namespace('dcterms', dcterms_ns)
    
    # Преобразуем обратно в строку
    xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')
    # Исправляем форматирование для соответствия оригиналу
    xml_str = xml_str.replace(' />', '/>')
    return xml_str


def generate_epub(
    template_epub: Path,
    blocks: list,
    output_epub: Path,
    title: str,
    author: str = "",
    cover_prompt: str = "",
    max_chapter_size_kb: int = 50,
):
    """Генерировать EPUB на основе шаблона и блоков текста"""
    
    # Разбиваем на разделы
    sections = split_into_chapters(blocks, max_size_kb=max_chapter_size_kb)
    print(f"Разбито на {len(sections)} глав (макс. {max_chapter_size_kb} KB)")
    
    # Создаем временную директорию
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Распаковываем шаблон EPUB
        with zipfile.ZipFile(template_epub, 'r') as z:
            z.extractall(tmp_path)
        
        oebps_path = tmp_path / "OEBPS"
        text_path = oebps_path / "Text"
        images_path = oebps_path / "Images"
        
        # Генерируем обложку
        has_cover_image = False
        if HAS_PIL:
            try:
                cover_image_data = generate_cover_image(title, author, prompt=cover_prompt)
                cover_image_path = images_path / "cover.jpg"
                cover_image_path.write_bytes(cover_image_data)
                has_cover_image = True
                print(f"Обложка создана: {cover_image_path}")
                
                # Обновляем cover.xhtml для использования новой обложки
                cover_xhtml_path = text_path / "cover.xhtml"
                if cover_xhtml_path.exists():
                    cover_xhtml_content = cover_xhtml_path.read_text(encoding="utf-8")
                    # Обновляем заголовок
                    cover_xhtml_content = re.sub(
                        r'<title>.*?</title>',
                        f'<title>{hesc(title)}</title>',
                        cover_xhtml_content,
                        flags=re.DOTALL
                    )
                    # Удаляем старый img тег, если есть (оставляем только SVG)
                    cover_xhtml_content = re.sub(
                        r'<img[^>]*src="[^"]*cover[^"]*"[^>]*/>',
                        '',
                        cover_xhtml_content,
                        flags=re.IGNORECASE
                    )
                    # Обновляем ссылку на изображение в SVG
                    cover_xhtml_content = re.sub(
                        r'<image[^>]*xlink:href="[^"]*"[^>]*>',
                        '<image width="665" height="1000" xlink:href="../Images/cover.jpg"/>',
                        cover_xhtml_content,
                        flags=re.IGNORECASE
                    )
                    cover_xhtml_path.write_text(cover_xhtml_content, encoding="utf-8")
            except Exception as e:
                print(f"Предупреждение: не удалось создать обложку: {e}")
        else:
            print("Предупреждение: Pillow не установлен, обложка не будет создана")
        
        # Удаляем старые Section файлы
        for old_section in text_path.glob("Section*.xhtml"):
            old_section.unlink()
        
        # Читаем content.opf
        opf_path = oebps_path / "content.opf"
        opf_content = opf_path.read_text(encoding="utf-8")
        
        # Генерируем новые разделы
        section_files = []
        for i, chapter in enumerate(sections, 1):
            section_blocks = chapter.get("blocks", [])
            section_id = f"Chapter{i:04d}.xhtml"
            section_title = chapter.get("title") or title
            xhtml_content = create_xhtml_section(section_blocks, section_title)
            section_file = text_path / section_id
            section_file.write_text(xhtml_content, encoding="utf-8")
            section_files.append(section_id)
        
        # Обновляем титульную страницу
        titul_path = text_path / "Titul.xhtml"
        if titul_path.exists():
            titul_content = titul_path.read_text(encoding="utf-8")
            # Обновляем заголовок и автора
            titul_content = re.sub(r'<title>.*?</title>', f'<title>{hesc(title)}</title>', titul_content, flags=re.DOTALL)
            titul_content = re.sub(r'<h1>.*?</h1>', f'<h1>{hesc(title)}</h1>', titul_content, flags=re.DOTALL)
            if author:
                titul_content = re.sub(r'<p class="author">.*?</p>', f'<p class="author">{hesc(author)}</p>', titul_content, flags=re.DOTALL)
            titul_path.write_text(titul_content, encoding="utf-8")
        
        # Обновляем оглавление (toc.ncx)
        toc_path = oebps_path / "toc.ncx"
        if toc_path.exists():
            toc_content = toc_path.read_text(encoding="utf-8")
            toc_root = ET.fromstring(toc_content)
            ncx_ns = 'http://www.daisy.org/z3986/2005/ncx/'
            ncx_ns_map = {'ncx': ncx_ns}
            
            # Обновляем заголовок
            doc_title_elem = toc_root.find('.//ncx:docTitle', ncx_ns_map)
            if doc_title_elem is not None:
                doc_title_text = doc_title_elem.find('ncx:text', ncx_ns_map)
                if doc_title_text is not None:
                    doc_title_text.text = title
            
            # Обновляем navMap - удаляем старые разделы и добавляем новые
            nav_map = toc_root.find('.//ncx:navMap', ncx_ns_map)
            if nav_map is not None:
                # Удаляем старые navPoint для Section
                for nav_point in list(nav_map):
                    content = nav_point.find('ncx:content', ncx_ns_map)
                    if content is not None:
                        src = content.get('src', '')
                        if 'Chapter' in src:
                            nav_map.remove(nav_point)
                
                # Добавляем новые navPoint для разделов
                for i, (section_file, chapter) in enumerate(zip(section_files, sections), 1):
                    section_id = f"Chapter{i:04d}.xhtml"
                    section_title = chapter.get("title", title)
                    
                    nav_point = ET.SubElement(nav_map, f'{{{ncx_ns}}}navPoint')
                    nav_point.set('id', f'navPoint{i+1}')
                    nav_point.set('playOrder', str(i+1))
                    
                    nav_label = ET.SubElement(nav_point, f'{{{ncx_ns}}}navLabel')
                    nav_label_text = ET.SubElement(nav_label, f'{{{ncx_ns}}}text')
                    nav_label_text.text = section_title
                    
                    nav_content = ET.SubElement(nav_point, f'{{{ncx_ns}}}content')
                    nav_content.set('src', f'Text/{section_id}')
            
            ET.register_namespace('', ncx_ns)
            toc_xml = ET.tostring(toc_root, encoding='utf-8', xml_declaration=True).decode('utf-8')
            toc_path.write_text(toc_xml, encoding="utf-8")
        
        # Обновляем content.opf (с обложкой, если создана)
        updated_opf = update_content_opf(opf_content, section_files, title, author, has_cover_image, sections)
        opf_path.write_text(updated_opf, encoding="utf-8")
        
        # Собираем новый EPUB
        with zipfile.ZipFile(output_epub, 'w', zipfile.ZIP_DEFLATED) as z:
            # mimetype должен быть первым и без сжатия
            mimetype_path = tmp_path / "mimetype"
            if mimetype_path.exists():
                z.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            
            # Остальные файлы
            for file_path in tmp_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(tmp_path)
                    if rel_path.name != "mimetype":  # mimetype уже добавлен
                        z.write(file_path, rel_path)
        
        print(f"EPUB создан: {output_epub}")


def main():
    ap = argparse.ArgumentParser(
        description="Генерация EPUB на основе шаблона и текста из JSON, HTML или TXT"
    )
    ap.add_argument("--template", required=True, help="Путь к шаблону EPUB")
    ap.add_argument("--in", dest="inp", required=True, help="Входной файл: JSON (structured.json), HTML или TXT")
    ap.add_argument("--out", required=True, help="Выходной EPUB файл")
    ap.add_argument("--title", required=True, help="Заголовок книги")
    ap.add_argument("--author", default="", help="Автор книги (для обложки)")
    ap.add_argument("--cover-prompt", default="", help="Дополнительное описание желаемой обложки (palette/era/mood/decor)")
    ap.add_argument("--max-chapter-size", type=int, default=50, help="Максимальный размер главы в KB (по умолчанию 50)")
    args = ap.parse_args()
    
    template_epub = Path(args.template)
    input_file = Path(args.inp)
    output_epub = Path(args.out)
    
    if not template_epub.exists():
        print(f"Ошибка: шаблон EPUB не найден: {template_epub}")
        return 1
    
    if not input_file.exists():
        print(f"Ошибка: входной файл не найден: {input_file}")
        return 1
    
    # Загружаем блоки
    suffix = input_file.suffix.lower()
    if suffix == ".json":
        blocks = load_blocks_from_json(input_file)
    elif suffix in (".html", ".htm"):
        blocks = load_blocks_from_html(input_file)
    elif suffix == ".txt":
        text_content = input_file.read_text(encoding="utf-8")
        blocks = load_blocks_from_text(text_content)
    else:
        print(f"Ошибка: неподдерживаемый формат входного файла: {input_file.suffix}")
        print("Поддерживаются: .json, .html, .htm")
        return 1
    
    if not blocks:
        print("Ошибка: не найдено блоков текста")
        return 1
    
    print(f"Загружено {len(blocks)} блоков")
    
    # Генерируем EPUB
    generate_epub(
        template_epub,
        blocks,
        output_epub,
        args.title,
        args.author,
        cover_prompt=args.cover_prompt,
        max_chapter_size_kb=args.max_chapter_size,
    )
    
    return 0


if __name__ == "__main__":
    exit(main())

