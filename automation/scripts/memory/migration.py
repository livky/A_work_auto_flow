"""Explicit, offline memory migration with fixed previews and recovery receipts.

Packages carry one selected owner, its immutable HEAD-reachable history, and a
dependency inventory. They never recursively copy referenced original sources.
Imports only add absent files: conflicts are reported before any target writes.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import uuid
import zipfile

from . import contracts, owners
from .evidence_adapter import iter_refs
from .errors import MemoryError
from .store import MemoryStore, process_identity, utc_now

MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 10000
EXTRACTION_NAMESPACE = uuid.UUID("4e4124f2-0607-4bd3-bd42-5789fe5a1454")


def _service(root, service=None):
    if service is None:
        from .service import MemoryService
        service = MemoryService(root)
    return service


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _relative(root, path):
    path = Path(path)
    if path.is_absolute():
        try:
            path = path.relative_to(Path(root).resolve())
        except ValueError as exc:
            raise MemoryError("UNSAFE_PATH", "Migration output must stay within the selected workspace") from exc
    return owners.safe_path(root, path.as_posix())


def _json(raw):
    try:
        return json.loads(raw.decode("utf-8-sig"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeError) as exc:
        raise MemoryError("INTEGRITY_ERROR", "Migration JSON is malformed") from exc


def _sealed(value):
    result = deepcopy(value)
    result["plan_hash"] = contracts.canonical_hash(value)
    return result


def _verify_plan(value):
    if not isinstance(value, dict) or contracts.canonical_hash({key: item for key, item in value.items() if key != "plan_hash"}) != value.get("plan_hash"):
        raise MemoryError("INTEGRITY_ERROR", "Migration preview was modified")


def _history(store, owner):
    """Traverse only the verified parent chain, never an orphan commit directory."""
    snapshot = store.read_snapshot(owner)
    manifest, seen = snapshot["manifest"], set()
    while manifest:
        if manifest["commit_id"] in seen:
            raise MemoryError("INTEGRITY_ERROR", "Memory history contains a cycle")
        seen.add(manifest["commit_id"])
        for rid, entry in manifest["record_heads"].items():
            record = store._record(owner, rid, entry)
            errors = contracts.validate_schema(record, contracts.SCHEMA["$defs"]["MemoryRecord"], contracts.SCHEMA["$defs"])
            if errors:
                raise MemoryError("INTEGRITY_ERROR", "Stored memory schema is invalid", errors=errors)
        yield manifest
        parent = manifest["parent_commit_id"]
        manifest = store._manifest(owner, parent, manifest["parent_manifest_hash"]) if parent else None


def _legacy_targets(value):
    """Inventory explicit legacy links without resolving or reading originals.

    Legacy locators are not registered Memory Ref identities. Keep their exact
    spelling in the package inventory instead of inventing registry IDs/hashes.
    """
    found = set()
    if isinstance(value, dict):
        for key, items in value.items():
            if key in {"dependencies", "evidence_refs", "inputs", "artifacts"} and isinstance(items, list):
                for item in items:
                    target = item.get("target", item.get("path")) if isinstance(item, dict) else None
                    if isinstance(target, str) and target:
                        found.add(target)
            found.update(_legacy_targets(items))
    elif isinstance(value, list):
        for item in value:
            found.update(_legacy_targets(item))
    return found


def export_owner(root, owner_id, output, *, service=None):
    root, service = Path(root).resolve(), _service(root, service)
    owner = owners.resolve_owner(root, owner_id)
    if owner["temporary"] or not owner["persisted"]:
        raise MemoryError("INVALID_ARGUMENT", "Adopt and save the selected owner before exporting its memory")
    if owner["native_data"].get("sensitivity") == "restricted":
        raise MemoryError("ACCESS_DENIED", "Selected owner is outside the current readable scope")
    destination = _relative(root, output)
    if destination.exists():
        raise MemoryError("VERSION_CONFLICT", "Export destination already exists")
    store, home = service.store, owner["memory_home"]
    snapshot = store.read_snapshot(owner)
    selected = {owner["native_ref"]["path"], home + "/owner.json"}
    # A flat evidence sidecar may declare one controlled local document. Keep
    # that original path and byte content; no recursive dependency expansion.
    document = owner["native_data"].get("document_path")
    if document:
        selected.add(owners.safe_path(root, document).relative_to(root).as_posix())
    if snapshot["head"]:
        selected.add(home + "/HEAD.json")
    dependencies = {}
    for manifest in _history(store, owner):
        prefix = home + "/commits/" + manifest["commit_id"]
        selected.update({prefix + "/manifest.json", prefix + "/receipt.json"})
        for rid, entry in manifest["record_heads"].items():
            selected.add(home + "/" + entry["path"])
            record = store._record(owner, rid, entry)
            # An export contains immutable historical bytes, so partial
            # redaction would break its integrity. Refuse the entire package
            # if any selected revision is no longer authorized for reading.
            if record["sensitivity"] == "restricted":
                raise MemoryError("ACCESS_DENIED", "Selected history contains restricted memory")
            for ref in iter_refs(record):
                try:
                    service._resolve_ref(ref, {}, [])
                except MemoryError as exc:
                    if exc.code in {"ACCESS_DENIED", "UNSAFE_PATH"}:
                        raise
                dependencies[contracts.canonical_hash(ref)] = deepcopy(ref)
    receipt_dir = store.path(owner, "request-receipts")
    if receipt_dir.is_dir():
        for path in receipt_dir.iterdir():
            if not path.is_file() or path.suffix != ".json":
                raise MemoryError("INTEGRITY_ERROR", "Unexpected request-receipt entry")
            envelope = store.read_json(path)
            store._receipt(owner, snapshot, path.stem, envelope.get("request_hash"))
            selected.add(path.relative_to(root).as_posix())
    payload = {}
    for name in sorted(selected):
        path = owners.safe_path(root, name)
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise MemoryError("INVALID_ARGUMENT", "Selected controlled file is missing or exceeds export size limit", {"path": name})
        payload[name] = path.read_bytes()
    if sum(map(len, payload.values())) > MAX_PACKAGE_BYTES or len(payload) > MAX_ENTRIES:
        raise MemoryError("INVALID_ARGUMENT", "Selected owner exceeds bounded export size")
    # Verify the snapshot once more before shipping bytes; active saves are not
    # silently mixed with the earlier list of immutable committed files.
    if store.read_snapshot(owner)["head"] != snapshot["head"]:
        raise MemoryError("STALE_BASIS", "Owner changed during export")
    if any(_sha(owners.safe_path(root, name).read_bytes()) != _sha(raw) for name, raw in payload.items()):
        raise MemoryError("STALE_BASIS", "Selected native or memory file changed during export")
    internal_ids = {owner_id, *snapshot["records"].keys()}
    internal_ids.update(claim["claim_id"] for record in snapshot["records"].values() for claim in record["payload"].get("claims", []))
    omitted = [{"ref": ref, "reason": "referenced original or other owner not included"}
               for ref in dependencies.values() if ref["target_kind"] == "file" or ref["target_id"] not in internal_ids]
    omitted.extend({"legacy_target": target, "reason": "legacy dependency not copied; locator retained unchanged"}
                   for target in sorted(_legacy_targets(owner["native_data"]) - internal_ids - selected))
    manifest = {"schema_version": 1, "package_kind": "memory-owner", "owner_id": owner_id,
                "owner_type": owner["owner_type"], "native_ref": owner["native_ref"], "memory_home": home,
                "source_head": snapshot["head"], "files": {name: {"sha256": _sha(raw), "size": len(raw)} for name, raw in payload.items()},
                "dependencies": list(dependencies.values()), "omitted": omitted}
    manifest["manifest_hash"] = contracts.canonical_hash(manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", _bytes(manifest))
            for name, raw in payload.items():
                archive.writestr("files/" + name, raw)
        _load_package(temporary)  # Verify actual ZIP content, not the input map.
        os.link(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"package_path": str(destination), "sha256": _sha(destination.read_bytes()),
            "owner_id": owner_id, "files": len(payload), "omitted": omitted, "source_head": snapshot["head"]}


def _load_package(package):
    """Reject zip-slip, aliases, symlinks, bombs and unmanifested entries first."""
    package = Path(package).absolute()
    # Preserve and inspect the supplied path spelling before any resolve():
    # resolving first would hide a junction or symlink in a parent directory.
    for component in (package, *package.parents):
        try:
            metadata = component.lstat()
        except OSError as exc:
            raise MemoryError("UNSAFE_PATH", "Package path cannot be verified") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise MemoryError("UNSAFE_PATH", "Package path contains a link or reparse point")
    if package.is_symlink() or not package.is_file():
        raise MemoryError("UNSAFE_PATH", "Package must be an explicit regular file")
    # Bound the container itself as well as expanded entries: ZIP padding and
    # oversized central directories must not bypass the in-memory size budget.
    if package.stat().st_size > MAX_PACKAGE_BYTES:
        raise MemoryError("INTEGRITY_ERROR", "Package container exceeds bounded import size")
    try:
        with zipfile.ZipFile(package) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES + 1 or sum(info.file_size for info in entries) > MAX_PACKAGE_BYTES:
                raise MemoryError("INTEGRITY_ERROR", "Package exceeds bounded import size")
            names = set()
            for info in entries:
                name = info.filename
                # Validate against a harmless root; safe_path performs no writes.
                owners.safe_path(package.parent, name)
                if "\\" in name or name.casefold() in names or info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                    raise MemoryError("UNSAFE_PATH", "Duplicate, directory, alias or linked ZIP entry")
                names.add(name.casefold())
                if info.file_size > MAX_FILE_BYTES:
                    raise MemoryError("INTEGRITY_ERROR", "Package file exceeds bounded import size")
            if "manifest.json" not in names:
                raise MemoryError("INTEGRITY_ERROR", "Package manifest is missing")
            manifest = _json(archive.read("manifest.json"))
            required = {"schema_version", "package_kind", "owner_id", "owner_type", "native_ref", "memory_home",
                        "source_head", "files", "dependencies", "omitted", "manifest_hash"}
            if (not isinstance(manifest, dict) or set(manifest) != required or type(manifest["schema_version"]) is not int
                    or manifest["schema_version"] != 1 or manifest["package_kind"] != "memory-owner"
                    or not isinstance(manifest["files"], dict)
                    or contracts.canonical_hash({k: v for k, v in manifest.items() if k != "manifest_hash"}) != manifest["manifest_hash"]):
                raise MemoryError("INTEGRITY_ERROR", "Package manifest schema or fingerprint is invalid")
            descriptor = owners._descriptor_schema(view=True)
            for field in ("owner_id", "owner_type", "native_ref", "memory_home"):
                errors = contracts.validate_schema(manifest[field], descriptor["properties"][field], contracts.SCHEMA["$defs"])
                if errors:
                    raise MemoryError("INTEGRITY_ERROR", "Package owner locator is invalid", errors=errors)
            if not isinstance(manifest["dependencies"], list) or not isinstance(manifest["omitted"], list):
                raise MemoryError("INTEGRITY_ERROR", "Package dependency inventory is malformed")
            for ref in manifest["dependencies"]:
                if contracts.validate_schema(ref, contracts.SCHEMA["$defs"]["Ref"], contracts.SCHEMA["$defs"]):
                    raise MemoryError("INTEGRITY_ERROR", "Package dependency reference is malformed")
            for omitted in manifest["omitted"]:
                is_legacy = isinstance(omitted, dict) and set(omitted) == {"legacy_target", "reason"}
                valid_target = (isinstance(omitted["legacy_target"], str) and bool(omitted["legacy_target"])) if is_legacy else (
                    isinstance(omitted, dict) and set(omitted) == {"ref", "reason"} and omitted["ref"] in manifest["dependencies"])
                if not valid_target or not isinstance(omitted["reason"], str):
                    raise MemoryError("INTEGRITY_ERROR", "Package omitted dependency is malformed")
            expected = {"manifest.json", *("files/" + name for name in manifest["files"])}
            if {info.filename for info in entries} != expected:
                raise MemoryError("INTEGRITY_ERROR", "Package contains missing or undeclared files")
            payload = {}
            for name, metadata in manifest["files"].items():
                owners.safe_path(package.parent, name)
                raw = archive.read("files/" + name)
                if not isinstance(metadata, dict) or set(metadata) != {"sha256", "size"} or _sha(raw) != metadata["sha256"] or len(raw) != metadata["size"]:
                    raise MemoryError("INTEGRITY_ERROR", "Package file fingerprint is invalid", {"path": name})
                payload[name] = raw
    except (zipfile.BadZipFile, KeyError, TypeError, ValueError, OSError, RuntimeError) as exc:
        if isinstance(exc, MemoryError):
            raise
        raise MemoryError("INTEGRITY_ERROR", "Package cannot be verified") from exc
    return manifest, payload


def _mapped_owner(root, manifest, payload, path_mapping):
    """Map only the native locator; immutable content and historic refs stay put."""
    path_mapping = path_mapping or {}
    native = manifest["native_ref"]["path"]
    if not isinstance(path_mapping, dict) or set(path_mapping) - {native}:
        raise MemoryError("INVALID_ARGUMENT", "Path mapping accepts only the selected native file locator")
    mapped_native = path_mapping.get(native, native)
    owners.safe_path(root, mapped_native)
    new_home = owners._home(manifest["owner_type"], mapped_native, manifest["owner_id"])
    old_home = manifest["memory_home"]
    owner = _json(payload.get(old_home + "/owner.json", b""))
    if not isinstance(owner, dict) or owner.get("owner_id") != manifest["owner_id"] or owner.get("native_ref") != manifest["native_ref"] or owner.get("memory_home") != old_home:
        raise MemoryError("INTEGRITY_ERROR", "Owner descriptor differs from package manifest")
    owner["native_ref"] = dict(owner["native_ref"], path=mapped_native)
    owner["memory_home"] = new_home
    mapped = {}
    for name, raw in payload.items():
        if name == native:
            destination = mapped_native
        elif name.startswith(old_home + "/"):
            destination = new_home + name[len(old_home):]
        else:
            destination = name  # A declared flat document retains its own path.
        owners.safe_path(root, destination)
        if destination.casefold() in {item.casefold() for item in mapped}:
            raise MemoryError("UNSAFE_PATH", "Mapped package paths collide")
        descriptor_changed = mapped_native != native or new_home != old_home
        mapped[destination] = _bytes(owner) if name == old_home + "/owner.json" and descriptor_changed else raw
    return owner, mapped


def _validate_contents(manifest, payload, owner):
    """Validate history in an isolated temporary workspace, never target state."""
    with tempfile.TemporaryDirectory(prefix="memory-import-check-") as temp:
        root = Path(temp)
        for name, raw in payload.items():
            path = owners.safe_path(root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        # Native/descriptor adapter validation catches undeclared ownership and
        # inappropriate home paths before any target directory is created.
        actual = owners.resolve_owner(root, owner["owner_id"])
        store = MemoryStore(root)
        histories = list(_history(store, actual))
        current = store.read_snapshot(actual)
        if current["head"] != manifest["source_head"]:
            raise MemoryError("INTEGRITY_ERROR", "Imported HEAD differs from the selected source snapshot")
        allowed = {actual["native_ref"]["path"], actual["memory_home"] + "/owner.json"}
        document = actual["native_data"].get("document_path")
        if document:
            allowed.add(document)
        if current["head"]:
            allowed.add(actual["memory_home"] + "/HEAD.json")
        for history in histories:
            prefix = actual["memory_home"] + "/commits/" + history["commit_id"]
            allowed.update({prefix + "/manifest.json", prefix + "/receipt.json"})
            for entry in history["record_heads"].values():
                allowed.add(actual["memory_home"] + "/" + entry["path"])
            for request_id, entry in history["request_ledger"].items():
                store._receipt(actual, {"manifest": history}, request_id, entry["request_hash"])
        prefix = actual["memory_home"] + "/request-receipts/"
        for name in payload:
            if name.startswith(prefix) and "/" not in name[len(prefix):] and name.endswith(".json"):
                envelope = store.read_json(root / name)
                store._receipt(actual, current, Path(name).stem, envelope.get("request_hash"))
                allowed.add(name)
        if set(payload) != allowed:
            raise MemoryError("INTEGRITY_ERROR", "Package includes files outside selected committed memory")
        return current


def preview_import(root, package, path_mapping=None):
    root, package = Path(root).resolve(), Path(package).absolute()
    manifest, payload = _load_package(package)
    owner, mapped = _mapped_owner(root, manifest, payload, path_mapping)
    current = _validate_contents(manifest, mapped, owner)
    existing = owners.list_owners(root)
    matches = [item for item in existing if item["owner_id"] == owner["owner_id"]]
    if matches and matches[0]["native_ref"] != owner["native_ref"]:
        raise MemoryError("VERSION_CONFLICT", "The owner ID already belongs to another native locator")
    # A record/claim cannot be imported under a second owner even if its title
    # happens to match. Compare canonical identities, never display strings.
    imported_ids = set(current["records"])
    imported_ids.update(claim["claim_id"] for record in current["records"].values() for claim in record["payload"].get("claims", []))
    for other in existing:
        if other["owner_id"] == owner["owner_id"]:
            continue
        snapshot = MemoryStore(root).read_snapshot(other)
        other_ids = set(snapshot["records"])
        other_ids.update(claim["claim_id"] for record in snapshot["records"].values() for claim in record["payload"].get("claims", []))
        if imported_ids & other_ids:
            raise MemoryError("VERSION_CONFLICT", "Imported record or claim identity already belongs to another owner")
    files, missing = [], []
    for name, raw in mapped.items():
        path = owners.safe_path(root, name)
        present = path.exists()
        if present and (not path.is_file() or _sha(path.read_bytes()) != _sha(raw)):
            raise MemoryError("VERSION_CONFLICT", "Import would overwrite different existing content", {"path": name})
        files.append({"path": name, "sha256": _sha(raw), "size": len(raw), "action": "keep" if present else "create"})
    service = _service(root)
    for omitted in manifest["omitted"]:
        if "legacy_target" in omitted:
            # Merely copying a locator cannot establish its current version,
            # authorization or applicability on another machine. Report that
            # gap explicitly; a later evidence check can resolve it locally.
            missing.append({"legacy_target": omitted["legacy_target"], "code": "UNRESOLVED_REFERENCE",
                            "reason": "Legacy dependency was not copied; destination verification is required"})
            continue
        ref = omitted["ref"]
        try:
            service._resolve_ref(ref, {}, [])
        except MemoryError as exc:
            missing.append({"ref": ref, "code": exc.code, "reason": "Dependency was not included and is unavailable at destination"})
    return _sealed({"schema_version": 1, "operation": "import", "package_path": str(package), "package_hash": _sha(package.read_bytes()),
                    "owner_id": owner["owner_id"], "native_ref": owner["native_ref"], "memory_home": owner["memory_home"],
                    "path_mapping": path_mapping or {}, "files": sorted(files, key=lambda item: item["path"]),
                    "dependencies": manifest["dependencies"], "missing": missing, "writes": 0})


def _write_receipt(path, receipt):
    value = deepcopy(receipt)
    value["receipt_hash"] = contracts.canonical_hash(receipt)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def recover_import(root, receipt_path, *, dry_run=True):
    """Remove only import-created bytes still matching the saved recovery plan.

    Existing files are never restored from a guessed backup. If a user edited
    any imported file, refuse the entire rollback instead of deleting new work.
    """
    root = Path(root).resolve()
    path = _relative(root, receipt_path)
    if not path.is_relative_to(root / ".local/memory-migrations"):
        raise MemoryError("UNSAFE_PATH", "Recovery receipt is outside migration state")
    value = _json(path.read_bytes())
    if contracts.canonical_hash({key: item for key, item in value.items() if key != "receipt_hash"}) != value.get("receipt_hash"):
        raise MemoryError("INTEGRITY_ERROR", "Migration recovery receipt is damaged")
    targets = []
    for entry in value["files"]:
        if entry["action"] != "create":
            continue
        target = owners.safe_path(root, entry["path"])
        if target.exists():
            staged = owners.safe_path(path.parent / "staged", entry["path"])
            published = entry["path"] in value.get("published", [])
            if not published and (not staged.exists() or not os.path.samefile(staged, target)):
                raise MemoryError("VERSION_CONFLICT", "Recovery refuses a file not published by this import", {"path": entry["path"]})
            if not target.is_file() or _sha(target.read_bytes()) != entry["sha256"]:
                raise MemoryError("VERSION_CONFLICT", "Imported file was modified after the migration", {"path": entry["path"]})
            targets.append(target)
    if dry_run:
        return {"dry_run": True, "would_remove": [str(item.relative_to(root)) for item in targets], "writes": 0}
    # HEAD is removed first, so readers never observe a partially rolled-back
    # committed snapshot. All remaining deletions are exact, verified files.
    targets.sort(key=lambda item: (item.name != "HEAD.json", -len(item.parts)))
    for target in targets:
        target.unlink()
    for name in sorted(value.get("created_directories", []), key=lambda item: len(PurePosixPath(item).parts), reverse=True):
        target = owners.safe_path(root, name)
        if target.is_dir() and not any(target.iterdir()):
            target.rmdir()
    receipt = {key: item for key, item in value.items() if key != "receipt_hash"}
    receipt["status"] = "rolled_back"
    _write_receipt(path, receipt)
    return {"status": "rolled_back", "removed": len(targets), "receipt_path": str(path)}


def import_package(root, plan, *, dry_run=False, fault=None):
    root, fault = Path(root).resolve(), fault or (lambda _point: None)
    _verify_plan(plan)
    if plan.get("operation") != "import":
        raise MemoryError("INVALID_ARGUMENT", "Expected an import preview")
    package = Path(plan["package_path"])
    if _sha(package.read_bytes()) != plan["package_hash"]:
        raise MemoryError("STALE_BASIS", "Package changed after preview")
    current = preview_import(root, package, plan["path_mapping"])
    if current["plan_hash"] != plan["plan_hash"]:
        # Repeating a completed import is idempotent even though create→keep
        # actions changed. Every current file must still equal the package.
        if not all(item["action"] == "keep" for item in current["files"]):
            raise MemoryError("STALE_BASIS", "Import target changed after preview")
    if dry_run:
        return dict(current, dry_run=True)
    if all(item["action"] == "keep" for item in current["files"]):
        return {"status": "no_change", "owner_id": plan["owner_id"], "missing": current["missing"], "writes": 0}
    manifest, payload = _load_package(package)
    owner, mapped = _mapped_owner(root, manifest, payload, plan["path_mapping"])
    transaction = root / ".local/memory-migrations" / uuid.uuid4().hex
    transaction.mkdir(parents=True)
    stage = transaction / "staged"
    stage.mkdir()
    receipt_path = transaction / "receipt.json"
    receipt = {"schema_version": 1, "operation": "import", "owner_id": plan["owner_id"],
               "package_hash": plan["package_hash"], "status": "prepared", "files": current["files"],
               "created_directories": [], "published": [], "created_at": utc_now()}
    for entry in current["files"]:
        if entry["action"] == "create":
            staged = owners.safe_path(stage, entry["path"])
            staged.parent.mkdir(parents=True, exist_ok=True)
            with staged.open("xb") as stream:
                stream.write(mapped[entry["path"]])
                stream.flush()
                os.fsync(stream.fileno())
            if _sha(staged.read_bytes()) != entry["sha256"]:
                raise MemoryError("INTEGRITY_ERROR", "Staged import file differs from verified package")
    _write_receipt(receipt_path, receipt)
    lock_path = owners.safe_path(root, owner["memory_home"] + "/write.lock")
    locked = False

    def mkdirs(directory):
        pending = []
        while directory != root and not directory.exists():
            pending.append(directory)
            directory = directory.parent
        for directory in reversed(pending):
            owners.safe_path(root, directory.relative_to(root).as_posix())
            directory.mkdir()
            receipt["created_directories"].append(directory.relative_to(root).as_posix())
            _write_receipt(receipt_path, receipt)
    try:
        mkdirs(lock_path.parent)
        lock = {"pid": os.getpid(), "start_identity": process_identity(os.getpid()), "token": str(uuid.uuid4()),
                "owner_id": owner["owner_id"], "created_at": utc_now()}
        try:
            with lock_path.open("xb") as stream:
                stream.write(_bytes(lock))
        except FileExistsError as exc:
            raise MemoryError("LOCKED", "Destination owner is being written") from exc
        locked = True
        for entry in current["files"]:
            target = owners.safe_path(root, entry["path"])
            if entry["action"] == "keep" and (not target.is_file() or _sha(target.read_bytes()) != entry["sha256"]):
                raise MemoryError("STALE_BASIS", "Existing destination changed after preview")
        receipt["status"] = "publishing"
        _write_receipt(receipt_path, receipt)
        ordered = sorted(current["files"], key=lambda item: (item["path"].endswith("/HEAD.json"), item["path"]))
        for entry in ordered:
            if entry["action"] == "keep":
                continue
            target = owners.safe_path(root, entry["path"])
            mkdirs(target.parent)
            if target.exists():
                raise MemoryError("VERSION_CONFLICT", "Destination appeared after preview", {"path": entry["path"]})
            fault("before_file")
            # Exclusive hard-link publication is atomic on the target volume;
            # the same-volume staging directory never replaces existing files.
            os.link(owners.safe_path(stage, entry["path"]), target)
            receipt["published"].append(entry["path"])
            _write_receipt(receipt_path, receipt)
            fault("after_file")
        imported = owners.resolve_owner(root, owner["owner_id"])
        list(_history(MemoryStore(root), imported))
        receipt["status"] = "committed"
        _write_receipt(receipt_path, receipt)
        return {"status": "imported", "owner_id": owner["owner_id"], "receipt_path": str(receipt_path),
                "missing": current["missing"], "files_created": sum(item["action"] == "create" for item in current["files"])}
    except (OSError, MemoryError) as exc:
        if locked:
            lock_path.unlink()
            locked = False
        receipt["status"] = "failed"
        _write_receipt(receipt_path, receipt)
        try:
            recover_import(root, receipt_path, dry_run=False)
        except MemoryError as recovery_error:
            raise MemoryError("STORAGE_ERROR", "Import failed and recovery requires inspection", {"receipt_path": str(receipt_path), "recovery_code": recovery_error.code}) from exc
        if isinstance(exc, MemoryError):
            raise
        raise MemoryError("STORAGE_ERROR", "Import failed; newly imported files were rolled back", {"receipt_path": str(receipt_path)}) from exc
    finally:
        if locked:
            lock_path.unlink()


def _prior_extraction(service, owner, request):
    """Find deterministic extraction retries without an extra mutable ledger."""
    snapshot = service.store.read_snapshot(owner)
    ledger = (snapshot["manifest"] or {}).get("request_ledger", {})
    entry = ledger.get(request["request_id"])
    if not entry:
        return None
    for manifest in _history(service.store, owner):
        if manifest["commit_id"] == entry["commit_id"]:
            original = deepcopy(request)
            original["expected_head"] = manifest["parent_commit_id"]
            return service.store._receipt(owner, snapshot, request["request_id"], service.request_hash(original))
    raise MemoryError("INTEGRITY_ERROR", "Extraction receipt is no longer reachable")


def preview(root, request, source_ref, *, service=None):
    """Preview AI extraction from one registered source; no inferred facts added."""
    service = _service(root, service)
    request = deepcopy(request)
    if source_ref.get("target_kind") != "file":
        raise MemoryError("INVALID_ARGUMENT", "Extraction source must be an explicitly registered file")
    service._resolve_ref(source_ref, {}, [])
    for operation in request.get("operations", []):
        draft = operation.get("draft", {})
        if draft.get("kind") in {"review", "source"}:
            raise MemoryError("INVALID_ARGUMENT", "AI extraction creates interpretation records, not raw-source or review identities")
        # Attribution is safe to add; occurrences, failures, and review facts
        # remain exactly what the supplied draft says, including UnknownValue.
        source = dict(source_ref, relation="background")
        if source not in draft.get("sources", []):
            draft.setdefault("sources", []).append(source)
    identity = contracts.canonical_hash({"owner_id": request.get("owner_id"), "actor": request.get("actor"),
                                         "source_ref": source_ref, "operations": request.get("operations")})
    request["request_id"] = str(uuid.uuid5(EXTRACTION_NAMESPACE, identity))
    request["dry_run"] = False
    request = service._request(request)
    owner = owners.resolve_owner(service.root, request["owner_id"])
    prior = _prior_extraction(service, owner, request)
    result = {"valid": True, "no_change": True, "receipt": prior} if prior else service.validate_draft(request)
    return _sealed({"schema_version": 1, "operation": "extract", "source_ref": deepcopy(source_ref),
                    "request": request, "validation": result, "writes": 0})


def apply(root, plan, *, service=None):
    """Apply only a fixed extraction preview; originals are never modified."""
    service = _service(root, service)
    _verify_plan(plan)
    if plan.get("operation") != "extract":
        raise MemoryError("INVALID_ARGUMENT", "Expected an extraction preview")
    service._resolve_ref(plan["source_ref"], {}, [])
    owner = owners.resolve_owner(service.root, plan["request"]["owner_id"])
    prior = _prior_extraction(service, owner, plan["request"])
    if prior:
        return prior
    return service.commit(plan["request"])
