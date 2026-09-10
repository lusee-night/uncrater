from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from uncrater.schema_registry import BINDINGS_BY_KEY, PROVENANCE


REPO_ROOT = Path(__file__).resolve().parents[1]
ABI_PROBE = Path(__file__).parent / "abi" / "abi_probe.c"


def load_vendor_module():
    spec = importlib.util.spec_from_file_location(
        "uncrater_vendor_coreloop",
        REPO_ROOT / "scripts" / "vendor_coreloop.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the coreloop vendoring script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vendor_coreloop = load_vendor_module()

KEY_SIZES = {
    "203": {"startup_hello": 30, "meta_data": 254, "housekeeping_data_0": 709},
    "305": {"startup_hello": 30, "meta_data": 270, "housekeeping_data_0": 2571},
    "306-early": {
        "startup_hello": 30,
        "meta_data": 270,
        "housekeeping_data_0": 2571,
        "calibrator_metadata": 590,
    },
    "306-final": {
        "startup_hello": 30,
        "meta_data": 270,
        "housekeeping_data_0": 2692,
        "calibrator_metadata": 597,
    },
    "307": {
        "startup_hello": 30,
        "meta_data": 270,
        "housekeeping_data_0": 2692,
        "calibrator_metadata": 597,
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_probe_output(output: str):
    result = {}
    for line in output.splitlines():
        columns = line.split("\t")
        if columns[0] == "S":
            _, structure, size, alignment = columns
            result[structure] = {
                "size": int(size),
                "alignment": int(alignment),
                "fields": {},
            }
        else:
            _, structure, field, offset, size = columns
            result[structure]["fields"][field] = {
                "offset": int(offset),
                "size": int(size),
            }
    return result


def test_manifest_matches_every_bundled_ctypes_abi():
    for key, binding in BINDINGS_BY_KEY.items():
        abi = vendor_coreloop.canonical_abi(binding.pystruct)
        record = PROVENANCE["bindings"][key]
        assert set(record["abi"]) == {"sha256"}
        assert vendor_coreloop.sha256_json(abi) == record["abi"]["sha256"]


def test_manifest_stays_compact_and_records_every_fingerprint():
    manifest_path = REPO_ROOT / "uncrater" / "coreloop" / "provenance.json"
    raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.stat().st_size < 64 * 1024
    assert set(raw_manifest) == {"bindings", "format_version"}
    for record in raw_manifest["bindings"].values():
        assert "structures" not in record["abi"]
        assert set(record["semantic_fingerprints"]) == {
            "appids",
            "commands",
            "core_constants",
            "errors",
            "output_formats",
        }


def test_key_abi_sizes_are_frozen():
    for key, expected in KEY_SIZES.items():
        structures = vendor_coreloop.canonical_abi(BINDINGS_BY_KEY[key].pystruct)
        assert {name: structures[name]["size"] for name in expected} == expected


def test_every_recorded_generated_file_hash_matches_bundle():
    for key, record in PROVENANCE["bindings"].items():
        destination = vendor_coreloop.destination_for(key)
        assert set(record["generated_files"]) == set(vendor_coreloop.BUNDLE_OUTPUTS)
        for name, expected_hash in record["generated_files"].items():
            assert sha256_file(destination / name) == expected_hash


def test_manifest_records_exact_pins_and_ctypesgen_version():
    manifest_path = REPO_ROOT / "uncrater" / "coreloop" / "provenance.json"
    records = json.loads(manifest_path.read_text(encoding="utf-8"))["bindings"]
    assert set(records) == set(vendor_coreloop.PINNED_BINDINGS)
    for key, pin in vendor_coreloop.PINNED_BINDINGS.items():
        record = records[key]
        for name in (
            "canonical_schema_id",
            "accepted_reported_versions",
            "variant",
            "source_release",
            "source_commit",
            "signatures",
        ):
            assert record[name] == pin[name]
        assert (
            record["generation"]["ctypesgen_version"]
            == vendor_coreloop.EXPECTED_CTYPESGEN_VERSION
        )


def test_registry_signatures_match_vendored_provenance():
    for key, binding in BINDINGS_BY_KEY.items():
        signatures = [
            {
                "appid": signature.appid,
                "payload_length": signature.payload_length,
                **(
                    {}
                    if signature.housekeeping_type is None
                    else {"housekeeping_type": signature.housekeeping_type}
                ),
            }
            for signature in binding.signatures
        ]
        assert signatures == list(PROVENANCE["bindings"][key]["signatures"])


def test_all_relevant_uint64_fields_are_eight_bytes():
    for binding in BINDINGS_BY_KEY.values():
        abi = vendor_coreloop.canonical_abi(binding.pystruct)
        for structure, field in vendor_coreloop.UINT64_FIELDS:
            if structure in abi:
                assert abi[structure]["fields"][field]["size"] == 8


def available_coreloop_checkout() -> Path | None:
    configured = os.environ.get("CORELOOP_DIR")
    candidate = Path(configured) if configured else REPO_ROOT.parent / "coreloop"
    if (candidate / ".git").exists():
        return candidate
    return None


def available_ctypesgen() -> str | None:
    bundled = REPO_ROOT / ".venv" / "bin" / "ctypesgen"
    if bundled.is_file():
        return str(bundled)
    return shutil.which("ctypesgen")


@pytest.mark.parametrize("binding_key", tuple(BINDINGS_BY_KEY))
def test_static_c_probe_matches_ctypes_offsets(binding_key):
    coreloop = available_coreloop_checkout()
    compiler = shutil.which("cc")
    if coreloop is None or compiler is None:
        pytest.skip("local pinned coreloop checkout and C compiler are required")

    binding = BINDINGS_BY_KEY[binding_key]
    with tempfile.TemporaryDirectory(prefix=f"abi-test-{binding_key}-") as directory:
        root = Path(directory)
        source = root / "source"
        source.mkdir()
        vendor_coreloop.extract_commit(coreloop, binding.source_commit, source)
        executable = root / "abi_probe"
        command = [
            compiler,
            "-std=c11",
            "-I",
            str(source / "coreloop"),
            str(ABI_PROBE),
            "-o",
            str(executable),
        ]
        if binding_key in ("306-final", "307"):
            command.insert(1, "-DUNCRATER_FINAL_306_LAYOUT=1")
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output = subprocess.run(
            [str(executable)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout

    c_abi = parse_probe_output(output)
    ctypes_abi = vendor_coreloop.canonical_abi(binding.pystruct)
    for structure, c_structure in c_abi.items():
        assert c_structure["size"] == ctypes_abi[structure]["size"]
        assert c_structure["alignment"] == ctypes_abi[structure]["alignment"]
        for field, c_field in c_structure["fields"].items():
            assert c_field["offset"] == ctypes_abi[structure]["fields"][field]["offset"]
            assert c_field["size"] == ctypes_abi[structure]["fields"][field]["size"]


def test_vendor_check_regenerates_without_writing_repository():
    coreloop = available_coreloop_checkout()
    ctypesgen = available_ctypesgen()
    compiler = shutil.which("cc")
    if coreloop is None or ctypesgen is None or compiler is None:
        pytest.skip("vendor dependencies and local coreloop checkout are required")

    provenance_path = REPO_ROOT / "uncrater" / "coreloop" / "provenance.json"
    before = sha256_file(provenance_path)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "vendor_coreloop.py"),
            "--coreloop",
            str(coreloop),
            "--ctypesgen",
            ctypesgen,
            "--compiler",
            compiler,
            "--check",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    after = sha256_file(provenance_path)
    assert before == after
    assert "verified bindings" in result.stdout
