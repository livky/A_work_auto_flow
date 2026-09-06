"""只在安装阶段下载成熟的多语言模型；记录实际文件 SHA256，运行期离线加载。"""
import hashlib
import json
import os
import argparse
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HOME"] = str(BASE / "models/hf-cache")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="下载公开模型并更新校验清单；默认只预览")
    parser.add_argument("--revision", help="可选 Hugging Face commit/tag；省略时下载当前默认版本")
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps({"repository": "qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q",
                          "target": str(BASE / "models/multilingual-minilm"), "apply": False}))
        raise SystemExit(0)
    from huggingface_hub import snapshot_download
    target = BASE / "models/multilingual-minilm"
    path = snapshot_download("qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q", local_dir=target, revision=args.revision,
                             allow_patterns=["*.json", "*.txt", "model_optimized.onnx", "README.md"])
    files = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in target.rglob("*") if p.is_file() and ".cache" not in p.parts}
    record = {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
              "repository": "qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q",
              "dimensions": 384, "path": "services/qdrant/models/multilingual-minilm", "files": files}
    (BASE / "model-manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({"model": record["model"], "files": len(files), "path": str(target)}))
