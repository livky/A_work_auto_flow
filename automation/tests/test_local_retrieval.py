"""真实本地模型集成检查；临时语料不会混入业务知识或真实反馈。

源码单独迁移、尚未安装运行时时跳过；完整工作区必须运行这些测试。
禁止 socket 连接，验证向量化、OCR 与上下文链确实可离线完成。
"""
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_retrieval import r, ROOT


@unittest.skipUnless((ROOT / "services/qdrant/models/multilingual-minilm/model_optimized.onnx").exists(),
                     "需先安装工作区本地嵌入模型")
class LocalRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "retrieval").mkdir()
        cfg = r.config(ROOT)
        for key in ("path", "manifest"):
            cfg["embedding"][key] = str(ROOT / cfg["embedding"][key])
        r.write_json(self.root / "retrieval/config.json", cfg)
        r.write_json(self.root / "retrieval/sources.json", {"sources": []})
        (self.root / "retrieval/context-policy.json").write_bytes((ROOT / "retrieval/context-policy.json").read_bytes())
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("网络访问被测试禁止"))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        self.temp.cleanup()

    def put(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_offline_semantic_update_delete_filter_and_full_override(self):
        doc = self.put("core-algorithms/sensor/note.md", "# Calibration\nTemperature changes cause sensor bias. Compensate thermal drift before estimating position.")
        self.put("core-algorithms/sensor/module.json", json.dumps({"module_id": "MOD-sensor", "title": "Sensors"}))
        self.put("knowledge/bread.md", "# Kitchen\nMix flour and water to bake bread in an oven.")
        found = r.search(self.root, "温度变化导致传感器测量偏差如何补偿", limit=1, module="MOD-sensor")
        self.assertEqual(found["results"][0]["path"], str(doc))
        self.assertEqual(found["results"][0]["retrievers"], ["qdrant"])
        pack = r.assemble(self.root, found)
        self.assertEqual(pack["manifest"]["sources"][0]["mode"], "excerpt")
        self.assertIn("Compensate thermal drift", r.assemble(self.root, found, mode="full")["text"])
        self.assertEqual(r.index(self.root)["qdrant"]["updated_sources"], 0)
        doc.write_text("Calibration removed. Unrelated replacement.", encoding="utf-8")
        stale = r.assemble(self.root, found)
        self.assertEqual(stale["manifest"]["sources"][0]["mode"], "omitted")
        doc.unlink()
        result = r.search(self.root, "温度补偿", module="MOD-sensor")
        self.assertNotIn(str(doc), [h["path"] for h in result["results"]])
        self.assertGreaterEqual(r.index(self.root)["qdrant"]["points"], 1)

    def test_slide_ocr_locator_and_context_policy(self):
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1200, 180), "white")
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
        ImageDraw.Draw(img).text((25, 45), "THERMAL DRIFT 125", fill="black", font=font)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        path = self.root / "research/slides.pptx"
        path.parent.mkdir()
        # 最小有效解析夹具：原始图在第 1 页，另一页文本不能泄漏到片段上下文。
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("ppt/slides/slide1.xml", '<p:sld xmlns:p="p" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>Calibration experiment</a:t></p:sld>')
            z.writestr("ppt/slides/slide2.xml", '<p:sld xmlns:p="p" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>SECOND_PAGE_ONLY</a:t></p:sld>')
            z.writestr("ppt/slides/_rels/slide1.xml.rels", '<Relationships><Relationship Id="r1" Type="image" Target="../media/image1.png"/></Relationships>')
            z.writestr("ppt/media/image1.png", buffer.getvalue())
        found = r.search(self.root, "THERMAL DRIFT", limit=1)
        self.assertEqual(found["results"][0]["path"], str(path))
        pack = r.assemble(self.root, found)
        self.assertIn("THERMAL DRIFT", pack["text"])
        self.assertNotIn("SECOND_PAGE_ONLY", pack["text"])
        entry = pack["manifest"]["sources"][0]
        self.assertEqual(entry["locator"], "Slide 1")
        self.assertTrue(entry["assets"][0]["has_text"])
        self.assertTrue(Path(entry["assets"][0]["path"]).is_file())
        self.assertNotIn("base64", pack["text"])
        self.assertIn("SECOND_PAGE_ONLY", r.assemble(self.root, found, mode="full")["text"])

    def test_table_row_locators(self):
        # 表格行段应带位置；关键数值和字段名可检索，但不宣称公式已执行。
        self.put("research/measurements.csv", "sample,bias\nA,0.125\nB,0.250\n")
        found = r.search(self.root, "0.125", limit=1)
        pack = r.assemble(self.root, found)
        entry = pack["manifest"]["sources"][0]
        self.assertEqual(entry["mode"], "excerpt")
        self.assertTrue(entry["locator"])
        self.assertIn("0.125", pack["text"])

    def test_scanned_pdf_and_standalone_image_ocr(self):
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1200, 240), "white")
        ImageDraw.Draw(img).text((30, 65), "SENSOR OFFSET 25", fill="black",
                                font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 52))
        directory = self.root / "research"
        directory.mkdir()
        img.save(directory / "scan.pdf", format="PDF")
        img.save(directory / "scan.png")
        found = r.search(self.root, "SENSOR OFFSET", limit=2)
        self.assertEqual({Path(h["path"]).suffix for h in found["results"]}, {".pdf", ".png"})
        pack = r.assemble(self.root, found)
        self.assertEqual({e["locator"] for e in pack["manifest"]["sources"]}, {"Page 1", "Image 1"})
        self.assertTrue(all(e["assets"][0]["has_text"] for e in pack["manifest"]["sources"]))

    def test_xlsx_cached_formula_is_marked(self):
        path = self.root / "research/calibration.xlsx"
        path.parent.mkdir()
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
                <row r="1"><c r="A1" t="inlineStr"><is><t>offset-calibration</t></is></c></row>
                <row r="2"><c r="B2"><f>1+2</f><v>3</v></c></row>
                </sheetData></worksheet>''')
        found = r.search(self.root, "offset-calibration", limit=1)
        pack = r.assemble(self.root, found)
        self.assertIn("B2: 3 [formula=1+2; cached value]", pack["text"])
        self.assertTrue(pack["manifest"]["sources"][0]["extraction_warnings"])

    def test_corrupt_pdf_does_not_block_other_sources(self):
        self.put("research/bad.pdf", "not a PDF")
        good = self.put("research/good.md", "温漂补偿需要固定标定版本。")
        indexed = r.index(self.root)
        self.assertEqual(len(indexed["unavailable"]), 1)
        self.assertIn("材料抽取失败", indexed["unavailable"][0]["reason"])
        self.assertEqual(r.search(self.root, "温漂补偿", limit=1)["results"][0]["path"], str(good))

    def test_staged_engine_with_real_offline_vectors(self):
        import context_engine
        card = self.put("core-algorithms/sensor/README.md", "# Calibration\nTemperature changes cause sensor bias. Compensate thermal drift.")
        self.put("core-algorithms/sensor/module.json", json.dumps({"module_id": "MOD-SENSOR"}))
        self.put("core-algorithms/sensor/code/core.py", "def compensate(value, temperature):\n    return value - temperature * 0.1\n")
        first = context_engine.create(self.root, "温度变化导致传感器偏差如何补偿", module="MOD-SENSOR")
        self.assertTrue(first["vector_enabled"])
        entry = next(s for s in first["manifest"]["sources"] if s["path"] == str(card))
        self.assertEqual(entry["mode"], "full")
        next_pack = context_engine.feedback(self.root, first["context_id"], "unresolved", "assistant-observation", "需要检查标定系数来源")
        self.assertEqual(next_pack["stage"], "investigate")
