"""Synthetic tests for the private CDI corpus contract."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import struct
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import conftest as corpus_conftest
import corpus_support
from corpus_support import (
    CORPUS_ENV,
    TIER_ENV,
    CorpusConfigurationError,
    CorpusValidationError,
    TierCoverageError,
    UncuratedExpectationError,
    assert_tree_decoder_expectations,
    build_decoder_audit_report,
    build_tree_decoder_report,
    build_inventory_report,
    canonical_report_bytes,
    compute_tree_digest,
    config_from_sources,
    runtime_identity,
    select_correctness_trees,
    validate_corpus,
    write_report,
)


def synthetic_decoder_expectations() -> dict:
    product_names = (
        "science_metadata",
        "normal_spectrum_packets",
        "tr_spectrum_groups",
        "tr_spectrum_packets",
        "heartbeat_packets",
        "watchdog_packets",
        "housekeeping_packets",
        "waveform_packets",
        "waveform_metadata_packets",
        "waveform_groups",
        "calibrator_metadata_packets",
        "calibrator_debug_metadata",
        "calibrator_data_groups",
        "calibrator_pfb_groups",
        "calibrator_debug_groups",
        "zoom_packets",
        "grimm_packets",
    )
    return {
        "reported_schema_ids": ["0x307"],
        "selected_schema_ids": ["0x307"],
        "selected_schema_bindings": ["307"],
        "schema_assumed": False,
        "packet_counts_by_appid": {"0x209": 1, "0x20F": 1},
        "invalid_counts_by_issue": {"bad_blob_length": 2},
        "product_counts": {name: 0 for name in product_names},
        "shapes": {
            "spectra": [],
            "tr_spectra": [],
            "waveforms": [],
            "zoom": [],
            "calibrator_data": [],
            "calibrator_pfb": [],
            "calibrator_aggregates": {
                name: [0]
                for name in (
                    "calib_data",
                    "calib_gNacc",
                    "calib_gphase",
                    "calib_pfb",
                    "cd_drift",
                    "cd_have_lock",
                    "cd_lock_ant",
                    "cd_error_phaser",
                    "cd_error_averager",
                    "cd_error_process",
                    "cd_error_stage3",
                    "cd_powertop0",
                    "cd_powertop1",
                    "cd_powertop2",
                    "cd_powertop3",
                    "cd_powerbot0",
                    "cd_powerbot1",
                    "cd_powerbot2",
                    "cd_powerbot3",
                    "cd_fd0",
                    "cd_fd1",
                    "cd_fd2",
                    "cd_fd3",
                    "cd_sd0",
                    "cd_sd1",
                    "cd_sd2",
                    "cd_sd3",
                    "cd_fdx",
                    "cd_sdx",
                    "cd_snr0",
                    "cd_snr1",
                    "cd_snr2",
                    "cd_snr3",
                )
            },
            "grimm": [],
        },
        "associations": {
            "science": [],
            "tr_spectra": [],
            "waveforms": [],
            "calibrator_data": [],
            "calibrator_pfb": [],
            "calibrator_debug": [],
        },
        "sentinels": [
            {
                "packet_index": 0,
                "appid": "0x209",
                "attribute": "reported_version",
                "index": [],
                "value": 0x307,
            }
        ],
    }


def reviewed_policy() -> dict:
    return {
        "curation_status": "reviewed",
        "expectations_generated_from_current_uncrater": False,
        "expected_outcome": "decode",
        "expectations": synthetic_decoder_expectations(),
        "schema_evidence": ["independently reviewed synthetic evidence"],
        "schema_hint": "current-307",
        "status": "correctness",
        "tags": ["synthetic", "v0307"],
        "tiers": ["smoke", "coverage"],
    }


def rejected_schema_policy(
    *,
    outcome: str,
    issue_code: str,
    reported_version: int,
    schema_classification: str,
) -> dict:
    policy = reviewed_policy()
    expectations = policy["expectations"]
    policy["expected_outcome"] = outcome
    policy["schema_hint"] = schema_classification
    policy["tags"] = ["synthetic", f"v{reported_version:04x}"]
    policy["tiers"] = []
    expectations["reported_schema_ids"] = [f"0x{reported_version:03X}"]
    expectations["selected_schema_ids"] = []
    expectations["selected_schema_bindings"] = []
    expectations["invalid_counts_by_issue"] = {issue_code: 1}
    expectations["sentinels"] = []
    return policy


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def packet_family(appid: int) -> str:
    if appid == 0x209:
        return "hello"
    if appid == 0x20F:
        return "science_metadata"
    return "control_or_other"


def make_corpus(
    parent: Path,
    *,
    identical_payloads: bool = False,
    policy: dict | None = None,
    reported_version: int = 0x307,
    schema_classification: str = "current-307",
    include_hello: bool = True,
) -> Path:
    root = parent / "private-corpus"
    trees_root = root / "trees"
    trees_root.mkdir(parents=True)

    version_text = f"0x{reported_version:03X}"
    hello_payload = struct.pack("<I", reported_version) + b"synthetic-hello"
    metadata_payload = (
        hello_payload
        if identical_payloads
        else struct.pack("<H", reported_version) + b"metadata"
    )
    payloads = {"00001_020f.bin": metadata_payload}
    if include_hello:
        payloads["00000_0209.bin"] = hello_payload
    files = []
    for name, payload in sorted(payloads.items()):
        appid = int(name.rsplit("_", 1)[1][:-4], 16)
        packet_index = int(name.split("_", 1)[0])
        files.append(
            {
                "appid": f"0x{appid:03X}",
                "hello_version": version_text if appid == 0x209 else None,
                "name": name,
                "packet_index": packet_index,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )

    digest = compute_tree_digest(files)
    tree_id = f"sha256:{digest}"
    tree_dir = trees_root / f"sha256-{digest}"
    payload_dir = tree_dir / "cdi_output"
    payload_dir.mkdir(parents=True)
    for name, payload in payloads.items():
        (payload_dir / name).write_bytes(payload)
    (tree_dir / "DESCRIPTION.txt").write_text(
        "Synthetic private-corpus contract fixture\n", encoding="utf-8"
    )

    appid_counts = Counter(item["appid"] for item in files)
    family_counts = Counter(packet_family(int(item["appid"], 16)) for item in files)
    test_policy = policy if policy is not None else {
        "curation_status": "not_curated",
        "expectations_generated_from_current_uncrater": False,
        "expected_outcome": None,
        "schema_evidence": ["synthetic inventory evidence"],
        "schema_hint": schema_classification,
        "status": "inventory_only",
        "tags": ["synthetic", "v0307"],
    }
    tree_manifest = {
        "file_count": len(files),
        "files": files,
        "manifest_schema_version": 1,
        "observations": {
            "duplicate_numeric_indices": [],
            "empty": False,
            "family_packet_counts": dict(sorted(family_counts.items())),
            "filename_appid_counts": dict(sorted(appid_counts.items())),
            "hello_packets": (
                [
                    {
                        "name": "00000_0209.bin",
                        "reported_sw_version": version_text,
                    }
                ]
                if include_hello else []
            ),
            "no_hello": not include_hello,
            "observed_appids": sorted(appid_counts, key=lambda item: int(item, 16)),
            "reported_sw_versions": [version_text] if include_hello else [],
        },
        "payload_path": "cdi_output",
        "private_data": True,
        "provenance": {
            "all_source_paths": ["/private/synthetic/source"],
            "canonical_source": "/private/synthetic/source",
            "copy_is_independent": True,
            "copy_verified_sha256": True,
            "source_instance_count": 1,
        },
        "publish_to_public_repository": False,
        "test_policy": test_policy,
        "total_bytes": sum(item["size_bytes"] for item in files),
        "tree_id": tree_id,
        "tree_id_algorithm": "lusee-cdi-tree-v1",
        "tree_id_contract": "Synthetic copy of the lusee-cdi-tree-v1 contract",
    }
    write_json(tree_dir / "manifest.json", tree_manifest)

    tree_entry = {
        "cdi_output": f"trees/sha256-{digest}/cdi_output",
        "families": sorted(family_counts),
        "manifest": f"trees/sha256-{digest}/manifest.json",
        "observed_appids": sorted(appid_counts, key=lambda item: int(item, 16)),
        "packet_file_count": len(files),
        "reported_hello_versions": [version_text] if include_hello else [],
        "schema_classification": schema_classification,
        "source_instance_count": 1,
        "total_bytes": sum(item["size_bytes"] for item in files),
        "tree_id": tree_id,
        "tree_sha256": digest,
    }
    top_manifest = {
        "all_source_packet_file_count": len(files),
        "all_source_total_bytes": sum(item["size_bytes"] for item in files),
        "corpus_root": str(root),
        "deduplicated_packet_file_count": len(files),
        "deduplicated_total_bytes": sum(item["size_bytes"] for item in files),
        "duplicate_content_group_count": 0,
        "duplicate_source_instance_count": 0,
        "exact_unique_tree_count": 1,
        "generated_at_utc": "2000-01-01T00:00:00+00:00",
        "manifest_version": 1,
        "private_data": True,
        "publish_to_public_repository": False,
        "source_directory_glob": "**/cdi_output*",
        "source_instance_count": 1,
        "source_search_root": "/private/synthetic",
        "tree_counts_by_family": {key: 1 for key in sorted(family_counts)},
        "tree_counts_by_reported_version": {
            version_text if include_hello else "none": 1
        },
        "trees": [tree_entry],
    }
    write_json(root / "corpus_manifest.json", top_manifest)
    return root


def tree_manifest_path(root: Path) -> Path:
    top = read_json(root / "corpus_manifest.json")
    return root / top["trees"][0]["manifest"]


def packet_path(root: Path, name: str) -> Path:
    top = read_json(root / "corpus_manifest.json")
    return root / top["trees"][0]["cdi_output"] / name


def run_real_data_pytest(
    *args: str,
    environ: dict[str, str] | None = None,
    target: str = "tests/real_data",
) -> subprocess.CompletedProcess[str]:
    """Run the real-data modules in an isolated child pytest session."""

    child_environ = os.environ.copy()
    child_environ.pop(CORPUS_ENV, None)
    child_environ.pop(TIER_ENV, None)
    child_environ["PYTEST_ADDOPTS"] = ""
    if environ is not None:
        child_environ.update(environ)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-rs",
            target,
            *args,
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=child_environ,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_config_unset_is_optional_and_defaults_to_full() -> None:
    config = config_from_sources({})
    assert config.root is None
    assert config.tier == "full"
    assert not config.require


def test_config_uses_only_declared_root_and_tier() -> None:
    config = config_from_sources(
        {CORPUS_ENV: "/configured/corpus", TIER_ENV: "coverage"}
    )
    assert config.root == Path("/configured/corpus")
    assert config.tier == "coverage"


def test_cli_tier_overrides_environment() -> None:
    config = config_from_sources(
        {CORPUS_ENV: "/configured/corpus", TIER_ENV: "coverage"},
        cli_tier="smoke",
    )
    assert config.tier == "smoke"


@pytest.mark.parametrize("tier", ["", "quick", "FULL", "../full"])
def test_invalid_tier_fails(tier: str) -> None:
    environ = {TIER_ENV: tier} if tier else {TIER_ENV: "invalid"}
    with pytest.raises(CorpusConfigurationError, match="invalid CDI tier"):
        config_from_sources(environ)


def test_require_flag_rejects_unset_root() -> None:
    with pytest.raises(CorpusConfigurationError, match=CORPUS_ENV):
        config_from_sources({}, require=True)


def test_unconfigured_real_data_module_skips_once() -> None:
    result = run_real_data_pytest()
    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "1 skipped" in output
    assert f"{CORPUS_ENV} is unset" in output


def test_unconfigured_regression_file_has_the_explicit_skip_reason() -> None:
    result = run_real_data_pytest(
        target="tests/real_data/test_cdi_regression.py"
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "1 skipped" in output
    assert f"{CORPUS_ENV} is unset" in output


def test_require_option_turns_an_unset_corpus_into_a_usage_error() -> None:
    result = run_real_data_pytest("--require-cdi-corpus")
    output = result.stdout + result.stderr

    assert result.returncode == pytest.ExitCode.USAGE_ERROR
    assert f"{CORPUS_ENV} is unset" in output


def test_configured_invalid_root_is_an_error_not_a_skip(tmp_path: Path) -> None:
    missing = tmp_path / "missing-corpus"
    result = run_real_data_pytest(environ={CORPUS_ENV: str(missing)})
    output = result.stdout + result.stderr

    assert result.returncode == pytest.ExitCode.USAGE_ERROR
    assert "missing corpus root" in output
    assert "skipped" not in output


def test_validated_corpus_is_cached_after_one_hash_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SimpleNamespace()
    setattr(
        config,
        corpus_conftest.CONFIG_ATTR,
        config_from_sources({CORPUS_ENV: str(tmp_path)}),
    )
    sentinel = object()
    calls: list[tuple[Path, bool]] = []

    def validate_once(root: Path, *, verify_hashes: bool) -> object:
        calls.append((root, verify_hashes))
        return sentinel

    monkeypatch.setattr(corpus_conftest, "validate_corpus", validate_once)

    assert corpus_conftest.get_validated_corpus(config) is sentinel
    assert corpus_conftest.get_validated_corpus(config) is sentinel
    assert calls == [(tmp_path, True)]


def test_valid_inventory_and_reports_are_deterministic(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    corpus = validate_corpus(root)
    report = build_inventory_report(corpus)
    first = canonical_report_bytes(report)
    second = canonical_report_bytes(build_inventory_report(corpus))

    assert first == second
    assert report["tree_count"] == 1
    assert report["packet_file_count"] == 2
    assert str(root).encode() not in first
    assert b"/private/synthetic" not in first

    output = write_report(report, tmp_path / "reports" / "inventory.json", corpus_root=root)
    assert output.read_bytes() == first
    with pytest.raises(CorpusConfigurationError, match="outside"):
        write_report(report, root / "forbidden.json", corpus_root=root)


def test_report_writer_rejects_a_dangling_symlink(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    report = build_inventory_report(validate_corpus(root))
    destination = tmp_path / "dangling-report.json"
    try:
        destination.symlink_to(tmp_path / "missing-target.json")
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(CorpusConfigurationError, match="symlink"):
        write_report(report, destination, corpus_root=root)


def test_detailed_report_is_sorted_and_contains_no_source_paths(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    corpus = validate_corpus(root)
    payload = canonical_report_bytes(build_inventory_report(corpus, detailed=True))
    assert corpus.trees[0].tree_id.encode() in payload
    assert b"/private/synthetic" not in payload


def test_runtime_identity_rejects_an_enclosing_git_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outer = tmp_path / "outer"
    source = outer / "uncrater-sdist"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        corpus_support,
        "__file__",
        str(source / "tests" / "corpus_support.py"),
    )

    def run_git(*args, **kwargs):
        return SimpleNamespace(stdout=str(outer) + "\n")

    monkeypatch.setattr(corpus_support.subprocess, "run", run_git)
    runtime_identity.cache_clear()
    try:
        assert runtime_identity()["uncrater_commit"] == "unknown"
    finally:
        runtime_identity.cache_clear()


def test_runtime_identity_marks_tracked_changes_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "uncrater"
    source.mkdir()
    monkeypatch.setattr(
        corpus_support,
        "__file__",
        str(source / "tests" / "corpus_support.py"),
    )
    commit = "a" * 40

    def run_git(command, **kwargs):
        if command[-1] == "--show-toplevel":
            return SimpleNamespace(stdout=str(source) + "\n")
        if command[-1] == "HEAD":
            return SimpleNamespace(stdout=commit + "\n")
        return SimpleNamespace(stdout=" M uncrater/Packet.py\n")

    monkeypatch.setattr(corpus_support.subprocess, "run", run_git)
    runtime_identity.cache_clear()
    try:
        assert runtime_identity()["uncrater_commit"] == commit + "-dirty"
    finally:
        runtime_identity.cache_clear()


@pytest.mark.parametrize(
    "field", ["manifest_version", "private_data", "publish_to_public_repository"]
)
def test_top_level_contract_flags_are_enforced(tmp_path: Path, field: str) -> None:
    root = make_corpus(tmp_path)
    path = root / "corpus_manifest.json"
    top = read_json(path)
    if field == "manifest_version":
        top[field] = 2
    else:
        top[field] = not top[field]
    write_json(path, top)
    with pytest.raises(CorpusValidationError):
        validate_corpus(root)


def test_tree_manifest_version_is_enforced(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    path = tree_manifest_path(root)
    manifest = read_json(path)
    manifest["manifest_schema_version"] = 2
    write_json(path, manifest)
    with pytest.raises(CorpusValidationError, match="unsupported tree manifest"):
        validate_corpus(root)


@pytest.mark.parametrize(
    "payload,match",
    [
        (b'{"manifest_version":1,"manifest_version":1}', "duplicate key"),
        (b'{"manifest_version":NaN}', "non-standard constant"),
    ],
)
def test_manifest_json_must_be_strict(
    tmp_path: Path, payload: bytes, match: str
) -> None:
    root = make_corpus(tmp_path)
    (root / "corpus_manifest.json").write_bytes(payload)
    with pytest.raises(CorpusValidationError, match=match):
        validate_corpus(root)


@pytest.mark.parametrize(
    "field,value",
    [
        ("manifest", "/absolute/manifest.json"),
        ("manifest", "../outside/manifest.json"),
        ("cdi_output", "trees/../outside/cdi_output"),
        ("manifest", "C:/outside/manifest.json"),
    ],
)
def test_unsafe_top_level_paths_are_rejected(
    tmp_path: Path, field: str, value: str
) -> None:
    root = make_corpus(tmp_path)
    path = root / "corpus_manifest.json"
    top = read_json(path)
    top["trees"][0][field] = value
    write_json(path, top)
    with pytest.raises(CorpusValidationError, match="path|absolute|escape"):
        validate_corpus(root)


def test_symlinked_packet_is_rejected(tmp_path: Path) -> None:
    root = make_corpus(tmp_path, identical_payloads=True)
    first = packet_path(root, "00000_0209.bin")
    second = packet_path(root, "00001_020f.bin")
    second.unlink()
    try:
        second.symlink_to(first.name)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(CorpusValidationError, match="symlink"):
        validate_corpus(root)


def test_symlinked_payload_directory_is_rejected(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    payload_dir = packet_path(root, "00000_0209.bin").parent
    real_dir = payload_dir.with_name("payload-copy")
    payload_dir.rename(real_dir)
    try:
        payload_dir.symlink_to(real_dir.name, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    with pytest.raises(CorpusValidationError, match="symlink"):
        validate_corpus(root)


def test_corpus_root_with_symlinked_ancestor_is_rejected(tmp_path: Path) -> None:
    real_parent = tmp_path / "real-parent"
    root = make_corpus(real_parent)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real_parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(CorpusValidationError, match="symlink"):
        validate_corpus(alias / root.name)


def test_hardlinked_packet_is_rejected(tmp_path: Path) -> None:
    root = make_corpus(tmp_path, identical_payloads=True)
    first = packet_path(root, "00000_0209.bin")
    second = packet_path(root, "00001_020f.bin")
    second.unlink()
    try:
        os.link(first, second)
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")
    with pytest.raises(CorpusValidationError, match="hardlink|inode"):
        validate_corpus(root)


@pytest.mark.parametrize("kind", ["nested", "nonpacket"])
def test_unmanifested_payload_content_is_rejected(tmp_path: Path, kind: str) -> None:
    root = make_corpus(tmp_path)
    payload_dir = packet_path(root, "00000_0209.bin").parent
    if kind == "nested":
        (payload_dir / "nested").mkdir()
    else:
        (payload_dir / "notes.txt").write_text("not a packet", encoding="utf-8")
    with pytest.raises(CorpusValidationError, match="nested|non-packet"):
        validate_corpus(root)


@pytest.mark.parametrize("kind", ["description", "manifest", "packet"])
def test_missing_required_tree_content_is_rejected(tmp_path: Path, kind: str) -> None:
    root = make_corpus(tmp_path)
    manifest = tree_manifest_path(root)
    if kind == "description":
        target = manifest.parent / "DESCRIPTION.txt"
    elif kind == "manifest":
        target = manifest
    else:
        target = packet_path(root, "00001_020f.bin")
    target.unlink()
    with pytest.raises(CorpusValidationError, match="missing|file count"):
        validate_corpus(root)


def test_packet_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    target = packet_path(root, "00001_020f.bin")
    target.write_bytes(b"X" * target.stat().st_size)
    with pytest.raises(CorpusValidationError, match="checksum"):
        validate_corpus(root)


@pytest.mark.parametrize(
    "field,bad_value,match",
    [
        ("appid", "0x210", "AppIDs disagree"),
        ("packet_index", 9, "packet indices disagree"),
        ("hello_version", "0x305", "Hello version"),
        ("size_bytes", 999, "byte size"),
    ],
)
def test_packet_inventory_fields_are_cross_checked(
    tmp_path: Path, field: str, bad_value: object, match: str
) -> None:
    root = make_corpus(tmp_path)
    path = tree_manifest_path(root)
    manifest = read_json(path)
    manifest["files"][0][field] = bad_value
    write_json(path, manifest)
    with pytest.raises(CorpusValidationError, match=match):
        validate_corpus(root)


def test_tree_inventory_must_be_filename_sorted(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    path = tree_manifest_path(root)
    manifest = read_json(path)
    manifest["files"].reverse()
    write_json(path, manifest)
    with pytest.raises(CorpusValidationError, match="filename-sorted"):
        validate_corpus(root)


@pytest.mark.parametrize(
    "observation,bad_value",
    [
        ("filename_appid_counts", {"0x209": 1}),
        ("family_packet_counts", {"hello": 2}),
        ("reported_sw_versions", ["0x305"]),
        ("observed_appids", ["0x209"]),
        ("duplicate_numeric_indices", [0]),
    ],
)
def test_observations_are_cross_checked(
    tmp_path: Path, observation: str, bad_value: object
) -> None:
    root = make_corpus(tmp_path)
    path = tree_manifest_path(root)
    manifest = read_json(path)
    manifest["observations"][observation] = bad_value
    write_json(path, manifest)
    with pytest.raises(CorpusValidationError, match="match|incorrect"):
        validate_corpus(root)


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("packet_file_count", 3),
        ("total_bytes", 999),
        ("observed_appids", ["0x209"]),
        ("reported_hello_versions", ["0x305"]),
        ("families", ["hello"]),
    ],
)
def test_top_tree_summary_is_cross_checked(
    tmp_path: Path, field: str, bad_value: object
) -> None:
    root = make_corpus(tmp_path)
    path = root / "corpus_manifest.json"
    top = read_json(path)
    top["trees"][0][field] = bad_value
    write_json(path, top)
    with pytest.raises(CorpusValidationError, match="top-level"):
        validate_corpus(root)


@pytest.mark.parametrize(
    "field",
    [
        "exact_unique_tree_count",
        "deduplicated_packet_file_count",
        "deduplicated_total_bytes",
        "source_instance_count",
        "all_source_packet_file_count",
        "all_source_total_bytes",
    ],
)
def test_bad_top_level_aggregate_is_rejected(tmp_path: Path, field: str) -> None:
    root = make_corpus(tmp_path)
    path = root / "corpus_manifest.json"
    top = read_json(path)
    top[field] += 1
    write_json(path, top)
    with pytest.raises(CorpusValidationError, match=field):
        validate_corpus(root)


def test_duplicate_tree_id_is_rejected(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    path = root / "corpus_manifest.json"
    top = read_json(path)
    top["trees"].append(copy.deepcopy(top["trees"][0]))
    write_json(path, top)
    with pytest.raises(CorpusValidationError, match="duplicate tree ID"):
        validate_corpus(root)


def test_duplicate_relative_payload_path_is_rejected(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    path = root / "corpus_manifest.json"
    top = read_json(path)
    duplicate = copy.deepcopy(top["trees"][0])
    duplicate["tree_id"] = "sha256:" + "f" * 64
    duplicate["manifest"] = "trees/alternate/manifest.json"
    top["trees"].append(duplicate)
    write_json(path, top)
    with pytest.raises(CorpusValidationError, match="duplicate relative payload"):
        validate_corpus(root)


def test_empty_top_level_tree_list_is_rejected(tmp_path: Path) -> None:
    root = make_corpus(tmp_path)
    path = root / "corpus_manifest.json"
    top = read_json(path)
    top["trees"] = []
    write_json(path, top)
    with pytest.raises(CorpusValidationError, match="at least one tree"):
        validate_corpus(root)


def test_full_correctness_tier_rejects_an_empty_selection(tmp_path: Path) -> None:
    corpus = validate_corpus(make_corpus(tmp_path))
    empty = replace(corpus, trees=(), packet_file_count=0, total_bytes=0)
    with pytest.raises(UncuratedExpectationError, match="no trees"):
        select_correctness_trees(empty, "full")


@pytest.mark.parametrize("tier", ["smoke", "coverage", "full"])
def test_inventory_only_corpus_fails_correctness_selection(
    tmp_path: Path, tier: str
) -> None:
    corpus = validate_corpus(make_corpus(tmp_path))
    with pytest.raises(UncuratedExpectationError):
        select_correctness_trees(corpus, tier)


def test_full_cli_tier_reports_the_uncurated_expectation_blocker(
    tmp_path: Path,
) -> None:
    root = make_corpus(tmp_path)
    result = run_real_data_pytest(
        "--cdi-tier",
        "full",
        "--require-cdi-corpus",
        environ={CORPUS_ENV: str(root)},
    )
    output = result.stdout + result.stderr

    assert result.returncode == pytest.ExitCode.INTERRUPTED
    assert "selected tree policies are not independently curated" in output


def test_curated_policy_is_selected_by_full_tier(tmp_path: Path) -> None:
    policy = reviewed_policy()
    corpus = validate_corpus(make_corpus(tmp_path, policy=policy))
    selected = select_correctness_trees(corpus, "full")
    assert [tree.tree_id for tree in selected] == [corpus.trees[0].tree_id]


@pytest.mark.parametrize("tier", ["smoke", "coverage"])
def test_minimal_curated_tree_cannot_claim_a_cross_tree_tier(
    tmp_path: Path, tier: str
) -> None:
    corpus = validate_corpus(make_corpus(tmp_path, policy=reviewed_policy()))
    with pytest.raises(TierCoverageError):
        select_correctness_trees(corpus, tier)


def smoke_contract_corpus(tmp_path: Path):
    corpus = validate_corpus(make_corpus(tmp_path, policy=reviewed_policy()))
    base = corpus.trees[0]

    def tree(
        suffix: str,
        *,
        version: str | None,
        outcome: str,
        binding: str | None = None,
        file_count: int = 1,
        tags: tuple[str, ...] = (),
    ):
        policy = reviewed_policy()
        policy["expected_outcome"] = outcome
        policy["tags"] = ["synthetic", *tags]
        policy["expectations"]["selected_schema_bindings"] = (
            [] if binding is None else [binding]
        )
        return replace(
            base,
            tree_id=f"synthetic-{suffix}",
            reported_versions=() if version is None else (version,),
            file_count=file_count,
            test_policy=policy,
        )

    trees = (
        tree(
            "307",
            version="0x307",
            outcome="decode",
            binding="307",
            tags=("broad-current-307",),
        ),
        tree("305", version="0x305", outcome="decode", binding="305"),
        tree(
            "306-early",
            version="0x306",
            outcome="decode",
            binding="306-early",
        ),
        tree("306-ambiguous", version="0x306", outcome="ambiguous_schema"),
        tree("partial", version=None, outcome="partial_session"),
        tree("empty", version=None, outcome="empty", file_count=0),
        tree("300", version="0x300", outcome="unsupported_schema"),
        tree("302", version="0x302", outcome="unsupported_schema"),
    )
    return replace(corpus, trees=trees)


def test_smoke_contract_requires_all_named_cases(tmp_path: Path) -> None:
    corpus = smoke_contract_corpus(tmp_path)
    selected = select_correctness_trees(corpus, "smoke")
    assert len(selected) == 8
    assert [tree.tree_id for tree in selected] == sorted(
        tree.tree_id for tree in selected
    )


def test_combined_decoder_report_is_canonical_across_input_order(
    tmp_path: Path,
) -> None:
    corpus = validate_corpus(make_corpus(tmp_path, policy=reviewed_policy()))
    reports = [{"tree_id": "tree-b"}, {"tree_id": "tree-a"}]

    first = build_decoder_audit_report(corpus, "full", reports)
    second = build_decoder_audit_report(corpus, "full", reversed(reports))

    assert canonical_report_bytes(first) == canonical_report_bytes(second)
    assert [tree["tree_id"] for tree in first["trees"]] == ["tree-a", "tree-b"]


def test_coverage_contract_rejects_unselected_observed_features(
    tmp_path: Path,
) -> None:
    corpus = smoke_contract_corpus(tmp_path)
    hidden = replace(
        corpus.trees[0],
        tree_id="synthetic-hidden-normal",
        reported_versions=("0x30A",),
        families=("normal_spectrum",),
        observed_appids=("0x210",),
        test_policy={**corpus.trees[0].test_policy, "tiers": []},
    )
    corpus = replace(corpus, trees=(*corpus.trees, hidden))

    with pytest.raises(TierCoverageError, match="reported versions|families"):
        select_correctness_trees(corpus, "coverage")


def test_coverage_contract_spans_inventory_schema_classifications(
    tmp_path: Path,
) -> None:
    corpus = smoke_contract_corpus(tmp_path)
    hidden = replace(
        corpus.trees[2],
        tree_id="synthetic-hidden-306-variant",
        schema_classification="final-306-layout",
        test_policy={**corpus.trees[2].test_policy, "tiers": []},
    )
    corpus = replace(corpus, trees=(*corpus.trees, hidden))

    with pytest.raises(TierCoverageError, match="schema classifications"):
        select_correctness_trees(corpus, "coverage")


def test_curated_decoder_report_is_checked_and_repeatable(tmp_path: Path) -> None:
    corpus = validate_corpus(make_corpus(tmp_path, policy=reviewed_policy()))
    tree = corpus.trees[0]

    first = build_tree_decoder_report(corpus, tree)
    second = build_tree_decoder_report(corpus, tree)

    assert canonical_report_bytes(first) == canonical_report_bytes(second)
    assert first["tree_id"] == tree.tree_id
    assert first["binding_provenance"][0]["binding_key"] == "307"
    assert str(corpus.root).encode() not in canonical_report_bytes(first)
    assert b"/private/synthetic" not in canonical_report_bytes(first)
    assert_tree_decoder_expectations(first, tree.test_policy)


@pytest.mark.parametrize(
    "reported_version,outcome,issue_code,schema_classification",
    [
        (0x300, "unsupported_schema", "unsupported_schema", "unsupported-300"),
        (0x306, "ambiguous_schema", "ambiguous_schema", "ambiguous-306"),
    ],
)
def test_nonstrict_schema_rejection_uses_collection_status(
    tmp_path: Path,
    reported_version: int,
    outcome: str,
    issue_code: str,
    schema_classification: str,
) -> None:
    policy = rejected_schema_policy(
        outcome=outcome,
        issue_code=issue_code,
        reported_version=reported_version,
        schema_classification=schema_classification,
    )
    corpus = validate_corpus(
        make_corpus(
            tmp_path,
            policy=policy,
            reported_version=reported_version,
            schema_classification=schema_classification,
        )
    )

    report = build_tree_decoder_report(corpus, corpus.trees[0])

    assert report["outcome"] == outcome
    assert report["packet_count"] == 0
    assert report["invalid_counts_by_issue"] == {issue_code: 1}
    assert_tree_decoder_expectations(report, corpus.trees[0].test_policy)


def test_no_hello_tree_produces_a_partial_session_report(tmp_path: Path) -> None:
    policy = reviewed_policy()
    policy["expected_outcome"] = "partial_session"
    policy["schema_hint"] = "no-hello-current-307"
    expectations = policy["expectations"]
    expectations["packet_counts_by_appid"] = {"0x20F": 1}
    expectations["invalid_counts_by_issue"] = {"bad_blob_length": 1}
    expectations["sentinels"] = [
        {
            "packet_index": 1,
            "appid": "0x20F",
            "attribute": "reported_version",
            "index": [],
            "value": 0x307,
        }
    ]
    corpus = validate_corpus(
        make_corpus(
            tmp_path,
            policy=policy,
            schema_classification="no-hello-current-307",
            include_hello=False,
        )
    )

    report = build_tree_decoder_report(corpus, corpus.trees[0])

    assert report["outcome"] == "partial_session"
    assert_tree_decoder_expectations(report, corpus.trees[0].test_policy)


def test_decoder_report_evaluates_scalar_and_hash_sentinels(tmp_path: Path) -> None:
    policy = reviewed_policy()
    hello_payload = struct.pack("<I", 0x307) + b"synthetic-hello"
    policy["expectations"]["sentinels"] = [
        {
            "packet_index": 0,
            "appid": "0x209",
            "attribute": "reported_version",
            "index": [],
            "value": 0x307,
            "nonzero": True,
        },
        {
            "packet_index": 0,
            "appid": "0x209",
            "attribute": "blob",
            "index": [],
            "sha256": hashlib.sha256(hello_payload).hexdigest(),
        },
    ]
    corpus = validate_corpus(make_corpus(tmp_path, policy=policy))

    report = build_tree_decoder_report(corpus, corpus.trees[0])

    assert_tree_decoder_expectations(report, corpus.trees[0].test_policy)


def test_decoder_generated_expectations_are_rejected(tmp_path: Path) -> None:
    policy = {
        "curation_status": "reviewed",
        "expectations_generated_from_current_uncrater": True,
        "expected_outcome": "decode",
        "schema_evidence": ["synthetic evidence"],
        "schema_hint": "current-307",
        "status": "correctness",
        "tags": ["synthetic"],
        "tiers": ["smoke"],
    }
    with pytest.raises(CorpusValidationError, match="decoder under test"):
        validate_corpus(make_corpus(tmp_path, policy=policy))


def test_curated_policy_requires_complete_decoder_expectations(tmp_path: Path) -> None:
    policy = reviewed_policy()
    del policy["expectations"]["associations"]

    with pytest.raises(CorpusValidationError, match="missing keys"):
        validate_corpus(make_corpus(tmp_path, policy=policy))


def test_decoded_policy_requires_an_independent_scalar_sentinel(
    tmp_path: Path,
) -> None:
    policy = reviewed_policy()
    policy["expectations"]["sentinels"] = []

    with pytest.raises(CorpusValidationError, match="independent sentinels"):
        validate_corpus(make_corpus(tmp_path, policy=policy))


def test_decoder_expectation_mismatch_fails(tmp_path: Path) -> None:
    policy = reviewed_policy()
    policy["expectations"]["invalid_counts_by_issue"] = {}
    corpus = validate_corpus(make_corpus(tmp_path, policy=policy))
    report = build_tree_decoder_report(corpus, corpus.trees[0])

    with pytest.raises(AssertionError, match="invalid_counts_by_issue"):
        assert_tree_decoder_expectations(report, corpus.trees[0].test_policy)


def test_non_string_expected_outcome_is_rejected_cleanly(tmp_path: Path) -> None:
    policy = {
        "curation_status": "reviewed",
        "expectations_generated_from_current_uncrater": False,
        "expected_outcome": ["decode"],
        "schema_evidence": ["synthetic evidence"],
        "schema_hint": "current-307",
        "status": "correctness",
        "tags": ["synthetic"],
        "tiers": ["smoke"],
    }
    with pytest.raises(CorpusValidationError, match="expected outcome"):
        validate_corpus(make_corpus(tmp_path, policy=policy))


def test_policy_rejects_unknown_status_and_blank_schema_evidence(tmp_path: Path) -> None:
    policy = reviewed_policy()
    policy["status"] = "typo"
    with pytest.raises(CorpusValidationError, match="unsupported status"):
        validate_corpus(make_corpus(tmp_path / "unknown", policy=policy))

    policy = reviewed_policy()
    policy["schema_evidence"] = ["   "]
    with pytest.raises(CorpusValidationError, match="must not be blank"):
        validate_corpus(make_corpus(tmp_path / "blank", policy=policy))


@pytest.mark.parametrize(
    ("appid", "family"),
    [
        (0x2F0, "raw_adc_waveform"),
        (0x2F3, "raw_adc_waveform"),
        (0x4F0, "raw_adc_waveform"),
        (0x4F1, "control_or_other"),
        (0x4F2, "control_or_other"),
        (0x4F3, "control_or_other"),
    ],
)
def test_corpus_family_uses_only_the_exact_historical_dcb_alias(
    appid: int, family: str
) -> None:
    assert corpus_support._packet_family(appid) == family


def test_waveform_sentinel_allows_4f0_but_not_broader_dcb_appids() -> None:
    policy = reviewed_policy()
    base_sentinel = policy["expectations"]["sentinels"][0]

    policy["expectations"]["sentinels"] = [
        base_sentinel,
        {
            "packet_index": 2,
            "appid": "0x4F0",
            "attribute": "waveform",
            "index": [0],
            "nonzero": True,
        },
    ]
    corpus_support._validate_test_policy(
        policy, families=("raw_adc_waveform",)
    )

    policy["expectations"]["sentinels"][1]["appid"] = "0x4F1"
    with pytest.raises(CorpusValidationError, match="raw_adc_waveform"):
        corpus_support._validate_test_policy(
            policy, families=("raw_adc_waveform",)
        )
