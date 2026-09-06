"""把多格式资料转成可定位的页/幻灯片/表格片段及视觉资产引用。

所有解析只读取原件字节。图片写入可重建缓存，正文仅放 OCR、替代文字与位置，
不写 base64。OCR 不是图表理解：没有可读文字的图片仍明确保留待视觉检查标记。
"""
import csv
import hashlib
import io
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

FORMATS = {".pptx", ".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".xlsx", ".csv"}
_ENGINE = None


def ocr_image(raw, enabled):
    global _ENGINE
    if not enabled:
        return "", "OCR disabled"
    try:
        from rapidocr_onnxruntime import RapidOCR
        if _ENGINE is None:
            _ENGINE = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
        result, _ = _ENGINE(raw)
        return "\n".join(row[1] for row in (result or [])), "OCR text; verify against image"
    except Exception as exc:
        return "", f"OCR failed: {type(exc).__name__}: {exc}"


def unpack(package, name):
    info = package.getinfo(name)
    if info.file_size > 30_000_000:
        raise ValueError(f"压缩成员过大：{name}")
    return package.read(name)


def material(root, path, raw, cfg):
    units, assets, warnings = [], [], []
    digest = hashlib.sha256(raw).hexdigest()
    cache = root / "retrieval/generated/assets" / digest

    def asset(data, label, unit):
        if len(assets) >= cfg.get("max_visual_assets", 40):
            warnings.append(f"视觉资产数量达到上限：{label}")
            return "[visual omitted by asset limit]"
        from PIL import Image
        try:
            with Image.open(io.BytesIO(data)) as img:
                if img.width * img.height > 40_000_000:
                    raise ValueError("图片超过 4000 万像素")
                img = img.convert("RGB")
                img.thumbnail((2000, 2000))
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                converted = buffer.getvalue()
        except Exception as exc:
            warnings.append(f"{label}: image decode failed ({exc})")
            return f"[visual unreadable: {label}]"
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / (hashlib.sha256(converted).hexdigest()[:20] + ".png")
        if not target.exists():
            target.write_bytes(converted)
        text, state = ocr_image(converted, cfg.get("ocr_enabled", True))
        record = {"path": str(target), "unit": unit, "label": label, "ocr_status": state,
                  "has_text": bool(text.strip()), "visual_semantics": "not-interpreted"}
        assets.append(record)
        if not text.strip():
            warnings.append(f"{unit}/{label}: 无可检索图中文字，需按资产路径视觉检查")
        return f"[Image: {label}; asset={target}; {state}; visual semantics not interpreted]\n{text}"

    suffix = path.suffix.lower()
    if suffix == ".pptx":
        with zipfile.ZipFile(io.BytesIO(raw)) as package:
            names = set(package.namelist())
            slides = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+.xml", n)),
                            key=lambda n: int(re.search(r"slide(\d+)", n).group(1)))
            # 实际播放顺序由 presentation.xml 决定，重排幻灯片后文件编号可能不变。
            if "ppt/presentation.xml" in names and "ppt/_rels/presentation.xml.rels" in names:
                mapping = {r.attrib["Id"]: posixpath.normpath(posixpath.join("ppt", r.attrib["Target"]))
                           for r in ET.fromstring(unpack(package, "ppt/_rels/presentation.xml.rels"))
                           if r.attrib.get("TargetMode") != "External"}
                ppt = ET.fromstring(unpack(package, "ppt/presentation.xml"))
                ordered = [mapping.get(node.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
                           for node in ppt.iter() if node.tag.endswith("}sldId")]
                slides = [n for n in ordered if n in names]
            ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
            for number, name in enumerate(slides, 1):
                unit = f"Slide {number}"
                tree = ET.fromstring(unpack(package, name))
                text = "\n".join(t.text or "" for t in tree.findall(".//a:t", ns))
                # 替代文字帮助查图片，但不会被当成模型实际识图结果。
                alt = [node.attrib.get("descr", "") for node in tree.iter() if node.attrib.get("descr")]
                parts = [text, *alt]
                relname = posixpath.join(posixpath.dirname(name), "_rels", posixpath.basename(name) + ".rels")
                if relname in names:
                    for rel in ET.fromstring(unpack(package, relname)):
                        if rel.attrib.get("TargetMode") == "External":
                            continue
                        target = posixpath.normpath(posixpath.join(posixpath.dirname(name), rel.attrib.get("Target", "")))
                        if target not in names:
                            continue
                        kind = rel.attrib.get("Type", "").rsplit("/", 1)[-1]
                        if kind == "image":
                            parts.append(asset(unpack(package, target), target, unit))
                        elif kind in {"notesSlide", "chart"}:
                            related = ET.fromstring(unpack(package, target))
                            values = [n.text for n in related.iter() if n.tag.rsplit("}", 1)[-1] in {"t", "v"} and n.text]
                            parts.append(f"[{kind}]\n" + "\n".join(values))
                units.append((unit, "\n".join(parts)))
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        for number, page in enumerate(reader.pages, 1):
            unit = f"Page {number}"
            parts = [page.extract_text() or ""]
            try:
                for img in page.images:
                    parts.append(asset(img.data, img.name, unit))
            except Exception as exc:
                warnings.append(f"{unit}: 图片抽取失败 {exc}")
            if not any(p.strip() for p in parts):
                warnings.append(f"{unit}: 未提取到文字或图片；可能含矢量图、特殊字体或空白，需查看原页")
            units.append((unit, "\n".join(parts)))
    elif suffix in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
        units.append(("Image 1", path.stem + "\n" + asset(raw, path.name, "Image 1")))
    elif suffix == ".csv":
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
        header = rows[0] if rows else []
        for i in range(1, len(rows), 40):
            units.append((f"Rows {i+1}-{min(i+40, len(rows))}", "\n".join(" | ".join(row) for row in [header, *rows[i:i+40]])))
        if len(rows) == 1:
            units.append(("Header", " | ".join(header)))
    elif suffix == ".xlsx":
        with zipfile.ZipFile(io.BytesIO(raw)) as package:
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            names = set(package.namelist())
            shared = []
            if "xl/sharedStrings.xml" in names:
                tree = ET.fromstring(unpack(package, "xl/sharedStrings.xml"))
                shared = ["".join(n.itertext()) for n in tree.findall("s:si", ns)]
            sheet_names = {}
            if "xl/workbook.xml" in names and "xl/_rels/workbook.xml.rels" in names:
                mapping = {rel.attrib["Id"]: posixpath.normpath(posixpath.join("xl", rel.attrib["Target"])).lstrip("/")
                           for rel in ET.fromstring(unpack(package, "xl/_rels/workbook.xml.rels"))
                           if rel.attrib.get("TargetMode") != "External"}
                for sheet in ET.fromstring(unpack(package, "xl/workbook.xml")).findall(".//s:sheet", ns):
                    target = mapping.get(sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
                    if target:
                        sheet_names[target] = sheet.attrib.get("name", target)
            for name in sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+.xml", n)):
                tree = ET.fromstring(unpack(package, name))
                rows = []
                for row in tree.findall(".//s:row", ns):
                    cells = []
                    for cell in row.findall("s:c", ns):
                        value = cell.findtext("s:v", default="", namespaces=ns)
                        if cell.attrib.get("t") == "s":
                            value = shared[int(value)]
                        elif cell.attrib.get("t") == "inlineStr":
                            value = "".join(cell.itertext())
                        formula = cell.findtext("s:f", default="", namespaces=ns)
                        cells.append(f"{cell.attrib.get('r')}: {value}" + (f" [formula={formula}; cached value]" if formula else ""))
                    # 工作表允许稀疏行，使用原始行号，不能把第几个 XML 元素当 Excel 行号。
                    rows.append((row.attrib.get("r", "?"), " | ".join(cells)))
                for i in range(0, len(rows), 40):
                    batch = rows[i:i+40]
                    units.append((f"{sheet_names.get(name, Path(name).stem)} rows {batch[0][0]}-{batch[-1][0]}",
                                  "\n".join(text for _, text in batch)))
        warnings.append("XLSX 未执行公式或解释格式/图表；值是文件中的缓存，日期可能为序列值")
    else:
        raise ValueError(f"无解析器：{suffix}")
    body, spans = "", []
    for label, text in units:
        start = len(body)
        body += f"\n## {label}\n{text.strip()}\n"
        spans.append({"label": label, "start": start, "end": len(body)})
    if not units:
        warnings.append("没有可抽取的页/行，需转换格式或补充说明")
    return body, {"units": spans, "assets": assets, "extraction_warnings": warnings}
