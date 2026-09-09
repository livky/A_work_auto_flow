"""仅用于浏览器验收的隔离记忆沙盒，不使用真实材料或预填复核通过。"""
from pathlib import Path
import sys
import tempfile
import json
import base64
import hashlib
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation/scripts"))
sys.path.insert(0, str(ROOT / "automation/tests"))
from memory_fixture import materialize
from memory.service import MemoryService
from memory import index
from memory import owners
import evidence
import workbench


def main():
    with tempfile.TemporaryDirectory(prefix="memory-browser-", dir=ROOT/".local") as temporary:
        fixture = materialize(Path(temporary)/"中文 记忆沙盒", isolation_root=temporary)
        # Workbench mutation receipts also refresh its material projection. A
        # minimal local retrieval boundary makes this a complete UI workspace;
        # it intentionally has no model or external source authorization.
        (fixture.root / "retrieval").mkdir(exist_ok=True)
        config = json.loads((ROOT / "retrieval/config.json").read_text(encoding="utf-8"))
        config.update(include_directories=[], vector_store={"provider": None})
        (fixture.root / "retrieval/config.json").write_text(
            json.dumps(config), encoding="utf-8")
        service = MemoryService(fixture.root)
        mapping = {}
        for theme in ("THERMAL", "PRESSURE"):
            request = fixture.request(["MEM-SRC-"+theme, "MEM-EXP-"+theme, "MEM-MAP-"+theme])
            # This UI variant explicitly supplies two shared problem keywords.
            # The frozen maps have no keywords and correctly yield no keyword
            # candidates; similarity must not be fabricated to satisfy the UI.
            request["operations"][2]["draft"]["keywords"] = ["前置条件", "适用边界"]
            if theme == "THERMAL":
                # Independent unreviewed synthetic claims allow the real UI to
                # exercise per-claim review without pre-filling acceptance.
                source = request["operations"][0]["draft"]["payload"]["source_ref"]
                for ref in request["operations"][1]["draft"]["sources"]:
                    # This UI-specific claim is about the marked text itself;
                    # the planned legacy Run remains background navigation.
                    ref["relation"] = "background"
                request["operations"][1]["draft"]["payload"]["claims"] = [
                    {"claim_id": "CLM-UI-" + str(number), "statement": "SYNTHETIC 界面结论 " + str(number),
                     "kind": "calculation", "scope": "SYNTHETIC browser only",
                     "evidence_refs": [{**source, "relation": "supports"}]}
                    for number in (1, 2, 3)]
            receipt = service.commit(request)
            mapping.update({r["client_key"]:r["record_id"] for r in receipt["record_results"]})
        # Browser-only L1 fixture: it documents a rendering test, never claims
        # the planned synthetic scientific Run has actually executed.
        owner = owners.resolve_owner(fixture.root, 'RES-SYN-THERMAL')
        image = fixture.root / Path(owner['native_ref']['path']).parent / 'figures' / 'synthetic.png'
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jP1sAAAAASUVORK5CYII='))
        registry_path = fixture.root / 'retrieval/sources.json'
        registry = json.loads(registry_path.read_text(encoding='utf-8'))
        registry['sources'].append({'source_id': 'SRC-UI-FIGURE', 'path': image.relative_to(fixture.root).as_posix(), 'enabled': True})
        registry_path.write_text(json.dumps(registry), encoding='utf-8')
        run = next(v for v in owners.list_owners(fixture.root) if v['owner_type'] == 'run')
        run_ref = {'target_kind': 'owner', 'target_id': run['owner_id'], 'revision': None,
                   'sha256': evidence.fingerprint(run['native_data']), 'locator': 'metadata', 'relation': 'background'}
        image_ref = {'target_kind': 'file', 'target_id': 'SRC-UI-FIGURE', 'revision': None,
                     'sha256': hashlib.sha256(image.read_bytes()).hexdigest(), 'locator': 'synthetic figure', 'relation': 'input'}
        draft = {'schema_version': 2, 'owner_id': owner['owner_id'], 'kind': 'detail', 'title': 'SYNTHETIC L1 论文式过程记录',
                 'body_markdown': '## 可核验的展示说明\n\n本记录用于界面验证，不声称实验已执行。\n\n| 内容 | 状态 |\n|---|---|\n| 公式 | 合成展示 |\n| 固定图片 | 受控读取 |',
                 'sources': [run_ref, image_ref], 'record_reason': '合成浏览器质量验收', 'provenance_gap': '仅为界面测试，非研究结论',
                 'sensitivity': 'internal', 'discovery': 'workspace_summary',
                 'payload': {'run_ref': run_ref, 'question': '研究步骤和参数能否完整呈现', 'method': '合成结构化文稿渲染',
                             'steps': ['显示重要入参及单位', '显示公式、变量和受控图片'], 'inputs': [image_ref],
                             'parameters': [{'name': 'n', 'value': 3, 'unit': '1', 'description': '合成参数的项数'}],
                             'formulas': [{'latex': 's=\\sum_{i=1}^{n}x_i', 'variables': [{'symbol': 's', 'meaning': '示例求和结果', 'unit': '1'}]}],
                             'figures': [{'caption': 'SYNTHETIC 固定像素图，仅验证图像读取', 'ref': image_ref}],
                             'results': '仅检验文稿展示；不宣称原 Run 已执行。', 'limitations': ['合成输入，不能据此判断科学算法有效性'], 'missing_refs': []}}
        head = service.store.read_snapshot(owner)['head']
        service.commit({'schema_version': 2, 'request_id': str(uuid.uuid4()), 'owner_id': owner['owner_id'],
                        'expected_head': head['commit_id'], 'actor': {'kind': 'workflow', 'id': 'synthetic-browser'},
                        'operations': [{'op': 'put_record', 'client_key': 'ui-detail', 'draft': draft}]})
        # The model-free browser fixture intentionally exercises the visible
        # pending-index state after edits. Real vectors are verified separately.
        index.rebuild(fixture.root, vector="off")
        (fixture.root/"synthetic-marker.json").write_text(json.dumps({"synthetic": True, "scope":"memory browser test"}), encoding="utf-8")
        print(json.dumps({"root": str(fixture.root), "mapping": mapping,
                          "source_paths": {key: value["path"] for key, value in fixture.sources.items()}}), flush=True)
        workbench.serve(fixture.root, open_browser=False)


if __name__ == "__main__":
    main()
