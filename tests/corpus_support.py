"""Read-only validation support for the private CDI regression corpus."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tempfile
from collections import Counter
from contextlib import redirect_stdout
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

import uncrater
from uncrater import Collection
from uncrater.schema_registry import (
    AmbiguousSchemaError,
    SchemaResolutionError,
)


CORPUS_ENV = "UNCRATER_CDI_CORPUS"
TIER_ENV = "UNCRATER_CDI_TIER"
CORPUS_MANIFEST_NAME = "corpus_manifest.json"
TREE_DIGEST_DOMAIN = b"lusee-cdi-tree-v1\0"
SUPPORTED_MANIFEST_VERSION = 1
SUPPORTED_TIERS = ("smoke", "coverage", "full")
SUPPORTED_OUTCOMES = {
    "decode",
    "unsupported_schema",
    "ambiguous_schema",
    "partial_session",
    "empty",
}
UNSUPPORTED_SCHEMA_ISSUES = frozenset(
    {"unsupported_schema", "unsupported_schema_variant", "unknown_schema"}
)

DECODER_EXPECTATION_KEYS = frozenset(
    {
        "reported_schema_ids",
        "selected_schema_ids",
        "selected_schema_bindings",
        "schema_assumed",
        "packet_counts_by_appid",
        "invalid_counts_by_issue",
        "product_counts",
        "shapes",
        "associations",
        "sentinels",
    }
)

PACKET_NAME_RE = re.compile(
    r"^(?P<packet_index>[0-9]+)_(?P<appid>[0-9A-Fa-f]{4})\.bin$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")
BROAD_CURRENT_307_TAG = "broad-current-307"
COMPRESSION_MODE_TAG_PREFIX = "compression-mode:"
AVERAGING_MODE_TAG_PREFIX = "averaging-mode:"


class CorpusError(ValueError):
    """Base class for corpus configuration and validation failures."""


class CorpusConfigurationError(CorpusError):
    """The requested corpus configuration is invalid."""


class CorpusValidationError(CorpusError):
    """The configured corpus does not satisfy its manifest contract."""


class UncuratedExpectationError(CorpusError):
    """A correctness tier selected trees without reviewed expectations."""


class TierCoverageError(CorpusError):
    """A curated tier does not meet its declared cross-tree coverage contract."""


@dataclass(frozen=True)
class CorpusConfig:
    """Resolved pytest configuration for optional private CDI tests."""

    root: Path | None
    tier: str
    require: bool
    report_dir: Path | None = None


@dataclass(frozen=True)
class CorpusFile:
    """One validated packet file and its immutable inventory metadata."""

    name: str
    path: Path
    packet_index: int
    appid: int
    size_bytes: int
    sha256: str
    hello_version: str | None


@dataclass(frozen=True)
class CorpusTree:
    """One exact-unique validated CDI packet tree."""

    tree_id: str
    manifest_path: Path
    payload_dir: Path
    description_path: Path
    file_count: int
    total_bytes: int
    files: tuple[CorpusFile, ...]
    families: tuple[str, ...]
    observed_appids: tuple[str, ...]
    reported_versions: tuple[str, ...]
    duplicate_numeric_indices: tuple[int, ...]
    family_packet_counts: Mapping[str, int]
    appid_packet_counts: Mapping[str, int]
    schema_classification: str
    test_policy: Mapping[str, Any]
    source_instance_count: int


@dataclass(frozen=True)
class ValidatedCorpus:
    """A fully validated read-only view of one configured corpus."""

    root: Path
    manifest_path: Path
    manifest_sha256: str
    manifest_version: int
    checksums_verified: bool
    trees: tuple[CorpusTree, ...]
    packet_file_count: int
    total_bytes: int
    source_instance_count: int


def config_from_sources(
    environ: Mapping[str, str] | None = None,
    *,
    cli_tier: str | None = None,
    require: bool = False,
    report_dir: str | os.PathLike[str] | None = None,
) -> CorpusConfig:
    """Resolve the sole corpus root and tier from environment and CLI inputs."""

    source = os.environ if environ is None else environ
    root_text = source.get(CORPUS_ENV, "").strip()
    env_tier = source.get(TIER_ENV, "").strip()
    tier = cli_tier or env_tier or "full"
    if tier not in SUPPORTED_TIERS:
        choices = ", ".join(SUPPORTED_TIERS)
        raise CorpusConfigurationError(
            f"invalid CDI tier {tier!r}; expected one of {choices}"
        )

    root = Path(root_text).expanduser() if root_text else None
    resolved_report_dir = (
        Path(report_dir).expanduser() if report_dir is not None else None
    )
    if require and root is None:
        raise CorpusConfigurationError(
            f"{CORPUS_ENV} is unset but --require-cdi-corpus was requested"
        )
    return CorpusConfig(
        root=root,
        tier=tier,
        require=require,
        report_dir=resolved_report_dir,
    )


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a regular file without modifying it."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def compute_tree_digest(files: Sequence[Mapping[str, Any] | CorpusFile]) -> str:
    """Compute the lusee-cdi-tree-v1 digest from a sorted file inventory."""

    digest = hashlib.sha256()
    digest.update(TREE_DIGEST_DOMAIN)
    normalized: list[tuple[str, int, str]] = []
    for item in files:
        if isinstance(item, CorpusFile):
            normalized.append((item.name, item.size_bytes, item.sha256))
        else:
            normalized.append(
                (str(item["name"]), int(item["size_bytes"]), str(item["sha256"]))
            )
    for name, size_bytes, file_sha256 in sorted(normalized):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size_bytes).encode("ascii"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(file_sha256))
    return digest.hexdigest()


def validate_corpus(
    root: str | os.PathLike[str], *, verify_hashes: bool = True
) -> ValidatedCorpus:
    """Validate a configured corpus without following links or writing files."""

    corpus_root = _resolve_directory_without_symlinks(
        Path(root).expanduser(), "corpus root"
    )

    manifest_path = _safe_existing_path(
        corpus_root, CORPUS_MANIFEST_NAME, kind="file", label="top-level manifest"
    )
    manifest_bytes = manifest_path.read_bytes()
    top = _load_json_bytes(manifest_bytes, "top-level manifest")
    _require_version(top, "manifest_version", "top-level manifest")
    _require_private_flags(top, "top-level manifest")
    for key in (
        "corpus_root",
        "generated_at_utc",
        "source_directory_glob",
        "source_search_root",
    ):
        _require_string(top, key, "top-level manifest")
    tree_entries = _require_list(top, "trees", "top-level manifest")
    if not tree_entries:
        raise CorpusValidationError("top-level manifest must list at least one tree")

    seen_tree_ids: set[str] = set()
    seen_manifest_paths: set[str] = set()
    seen_payload_paths: set[str] = set()
    seen_inodes: dict[tuple[int, int], str] = {}
    trees: list[CorpusTree] = []

    for ordinal, raw_entry in enumerate(tree_entries):
        label = f"tree entry {ordinal}"
        entry = _require_mapping(raw_entry, label)
        tree_id = _require_string(entry, "tree_id", label)
        if tree_id in seen_tree_ids:
            raise CorpusValidationError("duplicate tree ID in top-level manifest")
        seen_tree_ids.add(tree_id)

        manifest_rel = _require_relative_path(
            _require_string(entry, "manifest", label), f"{label} manifest path"
        )
        payload_rel = _require_relative_path(
            _require_string(entry, "cdi_output", label), f"{label} payload path"
        )
        if manifest_rel.as_posix() in seen_manifest_paths:
            raise CorpusValidationError("duplicate relative tree manifest path")
        if payload_rel.as_posix() in seen_payload_paths:
            raise CorpusValidationError("duplicate relative payload path")
        seen_manifest_paths.add(manifest_rel.as_posix())
        seen_payload_paths.add(payload_rel.as_posix())
        if manifest_rel.parent != payload_rel.parent:
            raise CorpusValidationError("tree manifest and payload must be siblings")
        if manifest_rel.name != "manifest.json" or payload_rel.name != "cdi_output":
            raise CorpusValidationError("tree layout must use manifest.json and cdi_output")

        tree_manifest_path = _safe_existing_path(
            corpus_root, manifest_rel, kind="file", label=f"{label} manifest"
        )
        payload_dir = _safe_existing_path(
            corpus_root, payload_rel, kind="directory", label=f"{label} payload"
        )
        description_path = _safe_existing_path(
            corpus_root,
            manifest_rel.parent / "DESCRIPTION.txt",
            kind="file",
            label=f"{label} description",
        )
        if not description_path.read_text(encoding="utf-8").strip():
            raise CorpusValidationError("tree description must not be empty")

        tree = _validate_tree(
            entry=entry,
            tree_id=tree_id,
            manifest_path=tree_manifest_path,
            payload_dir=payload_dir,
            description_path=description_path,
            verify_hashes=verify_hashes,
            seen_inodes=seen_inodes,
        )
        trees.append(tree)

    _validate_top_aggregates(top, trees)
    return ValidatedCorpus(
        root=corpus_root,
        manifest_path=manifest_path,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        manifest_version=SUPPORTED_MANIFEST_VERSION,
        checksums_verified=verify_hashes,
        trees=tuple(trees),
        packet_file_count=sum(tree.file_count for tree in trees),
        total_bytes=sum(tree.total_bytes for tree in trees),
        source_instance_count=sum(tree.source_instance_count for tree in trees),
    )


def select_correctness_trees(
    corpus: ValidatedCorpus, tier: str
) -> tuple[CorpusTree, ...]:
    """Select only explicitly tiered trees with independently curated policy."""

    if tier not in SUPPORTED_TIERS:
        raise CorpusConfigurationError(f"invalid CDI tier {tier!r}")
    if tier == "full":
        selected = list(corpus.trees)
    else:
        selected = [
            tree
            for tree in corpus.trees
            if tier in tuple(tree.test_policy.get("tiers", ()))
        ]
    if not selected:
        raise UncuratedExpectationError(
            f"no trees have explicit reviewed membership in the {tier!r} tier"
        )

    uncurated = [tree for tree in selected if not _policy_is_curated(tree.test_policy)]
    if uncurated:
        raise UncuratedExpectationError(
            f"{len(uncurated)} selected tree policies are not independently curated"
        )
    selected_tuple = tuple(sorted(selected, key=lambda tree: tree.tree_id))
    if tier == "smoke":
        _validate_smoke_coverage(selected_tuple)
    elif tier == "coverage":
        _validate_smoke_coverage(selected_tuple)
        _validate_full_observed_coverage(corpus, selected_tuple)
    return selected_tuple


def _validate_smoke_coverage(selected: Sequence[CorpusTree]) -> None:
    """Enforce the minimum independently curated smoke selection."""

    def bindings(tree: CorpusTree) -> set[str]:
        return set(tree.test_policy["expectations"]["selected_schema_bindings"])

    def outcome(tree: CorpusTree) -> str | None:
        return tree.test_policy.get("expected_outcome")

    missing: list[str] = []
    if not any(
        "0x307" in tree.reported_versions
        and "307" in bindings(tree)
        and BROAD_CURRENT_307_TAG in tree.test_policy.get("tags", ())
        for tree in selected
    ):
        missing.append(f"a 307 decode tagged {BROAD_CURRENT_307_TAG!r}")
    if not any("0x305" in tree.reported_versions and "305" in bindings(tree) for tree in selected):
        missing.append("a supported 305 decode")
    if not any(
        "0x306" in tree.reported_versions and "306-early" in bindings(tree)
        for tree in selected
    ):
        missing.append("an early-306 decode")
    if not any(
        "0x306" in tree.reported_versions and outcome(tree) == "ambiguous_schema"
        for tree in selected
    ):
        missing.append("an ambiguous-306 rejection")
    if not any(
        not tree.reported_versions
        and tree.file_count > 0
        and outcome(tree) == "partial_session"
        for tree in selected
    ):
        missing.append("a nonempty no-Hello partial session")
    if not any(tree.file_count == 0 and outcome(tree) == "empty" for tree in selected):
        missing.append("an empty tree")
    for version in ("0x300", "0x302"):
        if not any(
            version in tree.reported_versions
            and outcome(tree) == "unsupported_schema"
            for tree in selected
        ):
            missing.append(f"an unsupported {version} rejection")
    if missing:
        raise TierCoverageError("smoke tier is missing " + "; ".join(missing))


def _validate_full_observed_coverage(
    corpus: ValidatedCorpus, selected: Sequence[CorpusTree]
) -> None:
    """Require a coverage selection to span every observed corpus feature."""

    missing: list[str] = []
    all_versions = {version for tree in corpus.trees for version in tree.reported_versions}
    selected_versions = {
        version for tree in selected for version in tree.reported_versions
    }
    if selected_versions != all_versions:
        missing.append(
            "reported versions " + ", ".join(sorted(all_versions - selected_versions))
        )

    all_classifications = {tree.schema_classification for tree in corpus.trees}
    selected_classifications = {
        tree.schema_classification for tree in selected
    }
    if selected_classifications != all_classifications:
        missing.append(
            "schema classifications "
            + ", ".join(sorted(all_classifications - selected_classifications))
        )

    all_families = {family for tree in corpus.trees for family in tree.families}
    selected_families = {family for tree in selected for family in tree.families}
    if selected_families != all_families:
        missing.append("families " + ", ".join(sorted(all_families - selected_families)))

    all_priorities = _observed_spectrum_priorities(corpus.trees)
    selected_priorities = _observed_spectrum_priorities(selected)
    if selected_priorities != all_priorities:
        missing.append(
            "spectrum priorities "
            + ", ".join(sorted(all_priorities - selected_priorities))
        )

    for prefix, label in (
        (COMPRESSION_MODE_TAG_PREFIX, "compression modes"),
        (AVERAGING_MODE_TAG_PREFIX, "averaging modes"),
    ):
        all_tags, unclassified = _spectrum_mode_tags(corpus.trees, prefix)
        selected_tags, _ = _spectrum_mode_tags(selected, prefix)
        if unclassified:
            missing.append(
                f"{label} are undeclared for {len(unclassified)} spectrum trees"
            )
        elif selected_tags != all_tags:
            missing.append(label + " " + ", ".join(sorted(all_tags - selected_tags)))

    if any(tree.duplicate_numeric_indices for tree in corpus.trees) and not any(
        tree.duplicate_numeric_indices for tree in selected
    ):
        missing.append("a tied-index ordering case")

    if "raw_adc_waveform" in all_families and not any(
        tree.test_policy["expectations"]["associations"]["waveforms"]
        for tree in selected
        if "raw_adc_waveform" in tree.families
    ):
        missing.append("a positive waveform/metadata association")

    declared_final_306 = any(
        tree.test_policy.get("schema_variant") == "final"
        or "306-final"
        in tree.test_policy.get("expectations", {}).get(
            "selected_schema_bindings", ()
        )
        for tree in corpus.trees
    )
    if declared_final_306 and not any(
        "306-final"
        in tree.test_policy["expectations"]["selected_schema_bindings"]
        for tree in selected
    ):
        missing.append("a final-306 decode")

    if missing:
        raise TierCoverageError("coverage tier is missing " + "; ".join(missing))


def _observed_spectrum_priorities(trees: Sequence[CorpusTree]) -> set[str]:
    priorities: set[str] = set()
    ranges = (
        (0x210, 0x21F, "normal-high"),
        (0x220, 0x22F, "normal-medium"),
        (0x230, 0x23F, "normal-low"),
        (0x240, 0x24F, "tr-high"),
        (0x250, 0x25F, "tr-medium"),
        (0x260, 0x26F, "tr-low"),
    )
    for tree in trees:
        for appid_text in tree.observed_appids:
            appid = int(appid_text, 16)
            for start, stop, label in ranges:
                if start <= appid <= stop:
                    priorities.add(label)
                    break
    return priorities


def _spectrum_mode_tags(
    trees: Sequence[CorpusTree], prefix: str
) -> tuple[set[str], tuple[str, ...]]:
    tags: set[str] = set()
    unclassified: list[str] = []
    for tree in trees:
        if not ({"normal_spectrum", "time_resolved_spectrum"} & set(tree.families)):
            continue
        tree_tags = {
            tag
            for tag in tree.test_policy.get("tags", ())
            if tag.startswith(prefix) and len(tag) > len(prefix)
        }
        if not tree_tags:
            unclassified.append(tree.tree_id)
        tags.update(tree_tags)
    return tags, tuple(sorted(unclassified))


def build_inventory_report(
    corpus: ValidatedCorpus, *, detailed: bool = False
) -> dict[str, Any]:
    """Build a canonical path-free report from a validated inventory."""

    family_counts: Counter[str] = Counter()
    schema_counts: Counter[str] = Counter()
    version_counts: Counter[str] = Counter()
    policy_counts: Counter[str] = Counter()
    curation_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    ambiguous_order_count = 0

    for tree in corpus.trees:
        family_counts.update(tree.families)
        schema_counts[tree.schema_classification] += 1
        if tree.reported_versions:
            version_counts.update(tree.reported_versions)
        else:
            version_counts["none"] += 1
        policy_counts[str(tree.test_policy["status"])] += 1
        curation_counts[str(tree.test_policy["curation_status"])] += 1
        outcome = tree.test_policy.get("expected_outcome")
        outcome_counts["unset" if outcome is None else str(outcome)] += 1
        ambiguous_order_count += bool(tree.duplicate_numeric_indices)

    report: dict[str, Any] = {
        "report_schema_version": 1,
        "report_kind": "inventory",
        "corpus_manifest_sha256": corpus.manifest_sha256,
        "manifest_version": corpus.manifest_version,
        "checksums_verified": corpus.checksums_verified,
        "tree_count": len(corpus.trees),
        "packet_file_count": corpus.packet_file_count,
        "total_bytes": corpus.total_bytes,
        "source_instance_count": corpus.source_instance_count,
        "ordering_ambiguous_tree_count": ambiguous_order_count,
        "family_tree_counts": _sorted_counter(family_counts),
        "schema_classification_counts": _sorted_counter(schema_counts),
        "reported_version_tree_counts": _sorted_counter(version_counts),
        "policy_status_counts": _sorted_counter(policy_counts),
        "curation_status_counts": _sorted_counter(curation_counts),
        "expected_outcome_counts": _sorted_counter(outcome_counts),
    }
    if detailed:
        report["trees"] = [
            build_tree_inventory_report(tree)
            for tree in sorted(corpus.trees, key=lambda item: item.tree_id)
        ]
    return report


def build_tree_inventory_report(tree: CorpusTree) -> dict[str, Any]:
    """Build the deterministic inventory portion of one private tree report."""

    return {
        "tree_id": tree.tree_id,
        "schema_classification": tree.schema_classification,
        "file_count": tree.file_count,
        "total_bytes": tree.total_bytes,
        "families": list(tree.families),
        "reported_versions": list(tree.reported_versions),
        "duplicate_numeric_indices": list(tree.duplicate_numeric_indices),
        "family_packet_counts": dict(sorted(tree.family_packet_counts.items())),
        "appid_packet_counts": dict(sorted(tree.appid_packet_counts.items())),
        "test_policy": {
            "status": tree.test_policy["status"],
            "curation_status": tree.test_policy["curation_status"],
            "expected_outcome": tree.test_policy.get("expected_outcome"),
            "schema_hint": tree.test_policy.get("schema_hint"),
            "tiers": list(tree.test_policy.get("tiers", ())),
        },
    }


@lru_cache(maxsize=1)
def runtime_identity() -> dict[str, str]:
    """Return the package version and exact local source state without paths."""

    repository = Path(__file__).absolute().parents[1]
    commit = "unknown"
    try:
        top_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        top = Path(top_result.stdout.strip()).resolve()
        if top == repository.resolve():
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repository,
                check=True,
                capture_output=True,
                text=True,
            )
            candidate = commit_result.stdout.strip()
            if GIT_COMMIT_RE.fullmatch(candidate) is not None:
                dirty_result = subprocess.run(
                    ["git", "status", "--porcelain", "--untracked-files=no"],
                    cwd=repository,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                commit = candidate + ("-dirty" if dirty_result.stdout else "")
    except (OSError, subprocess.CalledProcessError, ValueError):
        commit = "unknown"
    return {"uncrater_version": uncrater.__version__, "uncrater_commit": commit}


def build_tree_decoder_report(
    corpus: ValidatedCorpus, tree: CorpusTree
) -> dict[str, Any]:
    """Decode one curated tree and return a canonical path-free audit report."""

    variant = tree.test_policy.get("schema_variant")
    try:
        with redirect_stdout(io.StringIO()):
            collection = Collection(
                tree.payload_dir,
                strict=False,
                schema_variant=None if variant is None else str(variant),
            )
    except AmbiguousSchemaError as exc:
        decoder = _rejected_decoder_fields(tree, exc)
        outcome = "ambiguous_schema"
        sentinels: list[dict[str, Any]] = []
    except SchemaResolutionError as exc:
        decoder = _rejected_decoder_fields(tree, exc)
        outcome = "unsupported_schema"
        sentinels = []
    else:
        decoder = collection.canonical_report()
        outcome = collection_outcome(collection, tree)
        sentinels = _evaluate_sentinels(
            collection, tree.test_policy["expectations"]["sentinels"]
        )

    report = {
        "report_schema_version": 1,
        "report_kind": "decoder_audit",
        "corpus_manifest_sha256": corpus.manifest_sha256,
        "tree_id": tree.tree_id,
        **runtime_identity(),
        "outcome": outcome,
        **decoder,
        "sentinels": sentinels,
    }
    return report


def collection_outcome(collection: Collection, tree: CorpusTree) -> str:
    """Classify a non-strict decode, including a collection skipped as unsafe."""

    if tree.file_count == 0:
        return "empty"
    issue_codes = set(collection.decode_status.codes)
    if not collection.cont:
        if "ambiguous_schema" in issue_codes:
            return "ambiguous_schema"
        if issue_codes & UNSUPPORTED_SCHEMA_ISSUES:
            return "unsupported_schema"
    if len(collection.cont) != tree.file_count or not tree.reported_versions:
        return "partial_session"
    return "decode"


def assert_tree_decoder_expectations(
    report: Mapping[str, Any], policy: Mapping[str, Any]
) -> None:
    """Require one actual decoder report to equal every curated expectation."""

    expected_outcome = policy["expected_outcome"]
    if report.get("outcome") != expected_outcome:
        raise AssertionError(
            f"decoder outcome {report.get('outcome')!r} != {expected_outcome!r}"
        )
    expectations = policy["expectations"]
    for key in sorted(DECODER_EXPECTATION_KEYS):
        actual = report.get(key)
        expected = expectations[key]
        if actual != expected:
            actual_json = json.dumps(actual, sort_keys=True, ensure_ascii=True)
            expected_json = json.dumps(expected, sort_keys=True, ensure_ascii=True)
            raise AssertionError(
                f"decoder report field {key!r} differs: "
                f"actual={actual_json}, expected={expected_json}"
            )


def build_decoder_audit_report(
    corpus: ValidatedCorpus,
    tier: str,
    tree_reports: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Combine sorted per-tree results into one deterministic private audit."""

    return {
        "report_schema_version": 1,
        "report_kind": "decoder_audit_collection",
        "corpus_manifest_sha256": corpus.manifest_sha256,
        "tier": tier,
        **runtime_identity(),
        "trees": sorted(
            (dict(report) for report in tree_reports),
            key=lambda report: str(report["tree_id"]),
        ),
    }


def _rejected_decoder_fields(
    tree: CorpusTree, error: SchemaResolutionError
) -> dict[str, Any]:
    reported_version = getattr(error, "reported_version", None)
    reported = list(tree.reported_versions)
    if reported_version is not None:
        rendered = f"0x{int(reported_version):03X}"
        if rendered not in reported:
            reported.append(rendered)
            reported.sort(key=_hex_sort_key)
    return {
        "reported_schema_ids": reported,
        "selected_schema_ids": [],
        "selected_schema_bindings": [],
        "schema_assumed": False,
        "binding_provenance": [],
        "packet_count": tree.file_count,
        "packet_counts_by_appid": dict(sorted(tree.appid_packet_counts.items())),
        "invalid_counts_by_issue": {},
        "orphan_multipart_failures": 0,
        "product_counts": _zero_product_counts(),
        "shapes": _empty_shapes(),
        "associations": _empty_associations(),
        "schema_error": {
            "type": type(error).__name__,
            "reported_version": (
                None
                if reported_version is None
                else f"0x{int(reported_version):03X}"
            ),
        },
    }


def _zero_product_counts() -> dict[str, int]:
    return {
        key: 0
        for key in (
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
    }


def _empty_shapes() -> dict[str, Any]:
    aggregate_names = (
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
    return {
        "spectra": [],
        "tr_spectra": [],
        "waveforms": [],
        "zoom": [],
        "calibrator_data": [],
        "calibrator_pfb": [],
        "calibrator_aggregates": {name: [0] for name in aggregate_names},
        "grimm": [],
    }


def _empty_associations() -> dict[str, Any]:
    return {
        "science": [],
        "tr_spectra": [],
        "waveforms": [],
        "calibrator_data": [],
        "calibrator_pfb": [],
        "calibrator_debug": [],
    }


def _evaluate_sentinels(
    collection: Collection, expected: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    for sentinel in expected:
        packet_index = int(sentinel["packet_index"])
        appid_text = sentinel.get("appid")
        candidates = [
            packet
            for packet in collection.cont
            if int(packet.packet_index) == packet_index
            and (
                appid_text is None
                or int(packet.original_appid) == int(str(appid_text), 16)
            )
        ]
        if len(candidates) != 1:
            raise AssertionError(
                f"sentinel packet index {packet_index} selected {len(candidates)} packets"
            )
        packet = candidates[0]
        value: Any = packet
        attribute = str(sentinel["attribute"])
        for name in attribute.split("."):
            if not name or name.startswith("_") or not hasattr(value, name):
                raise AssertionError(
                    f"sentinel attribute {attribute!r} is unavailable on packet {packet_index}"
                )
            value = getattr(value, name)
        indices = tuple(int(index) for index in sentinel.get("index", ()))
        if indices:
            value = value[indices]

        item = {
            "packet_index": packet_index,
            "appid": f"0x{int(packet.original_appid):03X}",
            "attribute": attribute,
            "index": list(indices),
        }
        if "value" in sentinel:
            item["value"] = _json_value(value)
        if "sha256" in sentinel:
            item["sha256"] = hashlib.sha256(
                np.ascontiguousarray(np.asarray(value)).tobytes()
            ).hexdigest()
        if "nonzero" in sentinel:
            item["nonzero"] = bool(np.any(np.asarray(value) != 0))
        observed.append(item)
    return observed


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise AssertionError(f"sentinel value has unsupported type {type(value).__name__}")


def canonical_report_bytes(report: Mapping[str, Any]) -> bytes:
    """Serialize a report deterministically for comparison and local storage."""

    return (
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def write_report(
    report: Mapping[str, Any],
    output_path: str | os.PathLike[str],
    *,
    corpus_root: str | os.PathLike[str],
) -> Path:
    """Write a report atomically outside the read-only corpus root."""

    root = Path(corpus_root).expanduser().resolve()
    requested_destination = Path(output_path).expanduser()
    if requested_destination.is_symlink():
        raise CorpusConfigurationError("report destination must not be a symlink")
    destination = requested_destination.resolve()
    if destination == root or root in destination.parents:
        raise CorpusConfigurationError("reports must be written outside the corpus root")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_report_bytes(report)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=".uncrater-report-", delete=False
        ) as stream:
            stream.write(payload)
            temp_name = stream.name
        os.replace(temp_name, destination)
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)
    return destination


def _validate_tree(
    *,
    entry: Mapping[str, Any],
    tree_id: str,
    manifest_path: Path,
    payload_dir: Path,
    description_path: Path,
    verify_hashes: bool,
    seen_inodes: dict[tuple[int, int], str],
) -> CorpusTree:
    tree_manifest = _load_json_bytes(manifest_path.read_bytes(), "tree manifest")
    _require_version(tree_manifest, "manifest_schema_version", "tree manifest")
    _require_private_flags(tree_manifest, "tree manifest")
    if _require_string(tree_manifest, "tree_id", "tree manifest") != tree_id:
        raise CorpusValidationError("top-level and per-tree IDs disagree")
    if _require_string(tree_manifest, "tree_id_algorithm", "tree manifest") != (
        "lusee-cdi-tree-v1"
    ):
        raise CorpusValidationError("unsupported tree digest algorithm")
    _require_string(tree_manifest, "tree_id_contract", "tree manifest")
    payload_path_text = _require_string(tree_manifest, "payload_path", "tree manifest")
    if _require_relative_path(payload_path_text, "tree payload_path") != PurePosixPath(
        "cdi_output"
    ):
        raise CorpusValidationError("per-tree payload_path must be cdi_output")

    raw_files = _require_list(tree_manifest, "files", "tree manifest")
    files: list[CorpusFile] = []
    seen_names: set[str] = set()
    previous_name: str | None = None
    index_counts: Counter[int] = Counter()
    appid_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    hello_packets: list[dict[str, str]] = []

    actual_entries = sorted(payload_dir.iterdir(), key=lambda path: path.name)
    for actual in actual_entries:
        actual_stat = actual.lstat()
        if stat.S_ISLNK(actual_stat.st_mode):
            raise CorpusValidationError("payload entries must not be symlinks")
        if stat.S_ISDIR(actual_stat.st_mode):
            raise CorpusValidationError("nested payload directories are not allowed")
        if not stat.S_ISREG(actual_stat.st_mode):
            raise CorpusValidationError("payload entries must be regular packet files")
        if PACKET_NAME_RE.fullmatch(actual.name) is None:
            raise CorpusValidationError("payload contains a non-packet file")

    if len(raw_files) != len(actual_entries):
        raise CorpusValidationError("per-tree manifest file count does not match payload")

    for ordinal, raw_file in enumerate(raw_files):
        label = f"tree file entry {ordinal}"
        item = _require_mapping(raw_file, label)
        name = _require_string(item, "name", label)
        if name in seen_names:
            raise CorpusValidationError("duplicate packet filename in tree manifest")
        seen_names.add(name)
        if previous_name is not None and name <= previous_name:
            raise CorpusValidationError("tree file inventory must be filename-sorted")
        previous_name = name

        match = PACKET_NAME_RE.fullmatch(name)
        if match is None:
            raise CorpusValidationError("invalid packet filename in tree manifest")
        packet_index = int(match.group("packet_index"))
        appid = int(match.group("appid"), 16)
        if _require_int(item, "packet_index", label) != packet_index:
            raise CorpusValidationError("filename and manifest packet indices disagree")
        manifest_appid = _parse_appid(_require_string(item, "appid", label), label)
        if manifest_appid != appid:
            raise CorpusValidationError("filename and manifest AppIDs disagree")

        path = payload_dir / name
        file_stat = _lstat(path, f"packet {name}")
        if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
            raise CorpusValidationError("manifest packet is not a regular file")
        if file_stat.st_nlink != 1:
            raise CorpusValidationError("hardlinked payload files are not allowed")
        inode_key = (file_stat.st_dev, file_stat.st_ino)
        if inode_key in seen_inodes:
            raise CorpusValidationError("payload files must not share an inode")
        seen_inodes[inode_key] = name

        size_bytes = _require_int(item, "size_bytes", label)
        if file_stat.st_size != size_bytes:
            raise CorpusValidationError("packet byte size does not match manifest")
        expected_sha256 = _require_string(item, "sha256", label)
        if SHA256_RE.fullmatch(expected_sha256) is None:
            raise CorpusValidationError("packet SHA-256 is not canonical lowercase hex")
        if verify_hashes and sha256_file(path) != expected_sha256:
            raise CorpusValidationError("packet checksum does not match manifest")

        expected_hello = item.get("hello_version")
        if expected_hello is not None and not isinstance(expected_hello, str):
            raise CorpusValidationError("hello_version must be a string or null")
        observed_hello = _read_hello_version(path) if appid == 0x209 else None
        if expected_hello != observed_hello:
            raise CorpusValidationError("packet Hello version does not match manifest")

        normalized_appid = _format_appid(appid)
        index_counts[packet_index] += 1
        appid_counts[normalized_appid] += 1
        family_counts[_packet_family(appid)] += 1
        if observed_hello is not None:
            hello_packets.append(
                {"name": name, "reported_sw_version": observed_hello}
            )
        files.append(
            CorpusFile(
                name=name,
                path=path,
                packet_index=packet_index,
                appid=appid,
                size_bytes=size_bytes,
                sha256=expected_sha256,
                hello_version=observed_hello,
            )
        )

    file_count = len(files)
    total_bytes = sum(item.size_bytes for item in files)
    if _require_int(tree_manifest, "file_count", "tree manifest") != file_count:
        raise CorpusValidationError("per-tree declared file count is incorrect")
    if _require_int(tree_manifest, "total_bytes", "tree manifest") != total_bytes:
        raise CorpusValidationError("per-tree declared byte count is incorrect")
    if _require_int(entry, "packet_file_count", "top-level tree entry") != file_count:
        raise CorpusValidationError("top-level tree file count is incorrect")
    if _require_int(entry, "total_bytes", "top-level tree entry") != total_bytes:
        raise CorpusValidationError("top-level tree byte count is incorrect")

    digest = compute_tree_digest(files)
    expected_tree_id = f"sha256:{digest}"
    if tree_id != expected_tree_id:
        raise CorpusValidationError("tree ID does not match its packet inventory")
    if _require_string(entry, "tree_sha256", "top-level tree entry") != digest:
        raise CorpusValidationError("top-level tree SHA-256 is incorrect")
    if manifest_path.parent.name != f"sha256-{digest}":
        raise CorpusValidationError("tree directory name does not match tree digest")

    observations = _require_mapping(
        tree_manifest.get("observations"), "tree observations"
    )
    duplicate_indices = tuple(
        sorted(index for index, count in index_counts.items() if count > 1)
    )
    _expect_equal_list(
        observations,
        "duplicate_numeric_indices",
        list(duplicate_indices),
        "duplicate numeric indices",
    )
    if _require_bool(observations, "empty", "tree observations") != (file_count == 0):
        raise CorpusValidationError("empty observation is incorrect")
    if _require_bool(observations, "no_hello", "tree observations") != (
        not hello_packets
    ):
        raise CorpusValidationError("no_hello observation is incorrect")
    _expect_equal_mapping(
        observations,
        "filename_appid_counts",
        _sorted_counter(appid_counts),
        "filename AppID counts",
    )
    _expect_equal_mapping(
        observations,
        "family_packet_counts",
        _sorted_counter(family_counts),
        "family packet counts",
    )
    observed_appids = tuple(sorted(appid_counts, key=_parse_appid_sort_key))
    _expect_equal_list(
        observations,
        "observed_appids",
        list(observed_appids),
        "observed AppIDs",
    )
    if observations.get("hello_packets") != hello_packets:
        raise CorpusValidationError("Hello packet observations are incorrect")
    reported_versions = tuple(
        sorted({item["reported_sw_version"] for item in hello_packets}, key=_hex_sort_key)
    )
    _expect_equal_list(
        observations,
        "reported_sw_versions",
        list(reported_versions),
        "reported SW versions",
    )

    top_families = tuple(_require_string_list(entry, "families", "tree entry"))
    expected_families = tuple(sorted(family_counts))
    if top_families != expected_families:
        raise CorpusValidationError("top-level tree families are incorrect")
    top_appids = tuple(
        _require_string_list(entry, "observed_appids", "tree entry")
    )
    if top_appids != observed_appids:
        raise CorpusValidationError("top-level observed AppIDs are incorrect")
    top_versions = tuple(
        _require_string_list(entry, "reported_hello_versions", "tree entry")
    )
    if top_versions != reported_versions:
        raise CorpusValidationError("top-level reported Hello versions are incorrect")

    policy = _validate_test_policy(
        _require_mapping(tree_manifest.get("test_policy"), "tree test policy"),
        families=tuple(sorted(family_counts)),
    )
    schema_classification = _require_string(
        entry, "schema_classification", "top-level tree entry"
    )
    schema_hint = policy.get("schema_hint")
    if schema_hint is not None and schema_hint != schema_classification:
        raise CorpusValidationError("schema classification and policy hint disagree")

    provenance = _require_mapping(
        tree_manifest.get("provenance"), "tree provenance"
    )
    source_instance_count = _require_int(
        provenance, "source_instance_count", "tree provenance"
    )
    source_paths = _require_string_list(
        provenance, "all_source_paths", "tree provenance"
    )
    if source_instance_count != len(source_paths) or len(source_paths) != len(
        set(source_paths)
    ):
        raise CorpusValidationError("tree provenance source count is inconsistent")
    canonical_source = _require_string(
        provenance, "canonical_source", "tree provenance"
    )
    if canonical_source not in source_paths:
        raise CorpusValidationError("canonical source is absent from provenance")
    if not _require_bool(provenance, "copy_is_independent", "tree provenance"):
        raise CorpusValidationError("payload copy is not marked independent")
    if not _require_bool(provenance, "copy_verified_sha256", "tree provenance"):
        raise CorpusValidationError("payload copy is not marked checksum-verified")
    if _require_int(entry, "source_instance_count", "top-level tree entry") != (
        source_instance_count
    ):
        raise CorpusValidationError("top-level tree source count is incorrect")

    return CorpusTree(
        tree_id=tree_id,
        manifest_path=manifest_path,
        payload_dir=payload_dir,
        description_path=description_path,
        file_count=file_count,
        total_bytes=total_bytes,
        files=tuple(files),
        families=expected_families,
        observed_appids=observed_appids,
        reported_versions=reported_versions,
        duplicate_numeric_indices=duplicate_indices,
        family_packet_counts=MappingProxyType(_sorted_counter(family_counts)),
        appid_packet_counts=MappingProxyType(_sorted_counter(appid_counts)),
        schema_classification=schema_classification,
        test_policy=MappingProxyType(dict(policy)),
        source_instance_count=source_instance_count,
    )


def _validate_top_aggregates(
    top: Mapping[str, Any], trees: Sequence[CorpusTree]
) -> None:
    tree_count = len(trees)
    packet_count = sum(tree.file_count for tree in trees)
    byte_count = sum(tree.total_bytes for tree in trees)
    source_count = sum(tree.source_instance_count for tree in trees)
    duplicate_source_count = source_count - tree_count
    duplicate_group_count = sum(tree.source_instance_count > 1 for tree in trees)
    all_source_packets = sum(
        tree.file_count * tree.source_instance_count for tree in trees
    )
    all_source_bytes = sum(
        tree.total_bytes * tree.source_instance_count for tree in trees
    )

    expected_ints = {
        "exact_unique_tree_count": tree_count,
        "deduplicated_packet_file_count": packet_count,
        "deduplicated_total_bytes": byte_count,
        "source_instance_count": source_count,
        "duplicate_source_instance_count": duplicate_source_count,
        "duplicate_content_group_count": duplicate_group_count,
        "all_source_packet_file_count": all_source_packets,
        "all_source_total_bytes": all_source_bytes,
    }
    for key, expected in expected_ints.items():
        if _require_int(top, key, "top-level manifest") != expected:
            raise CorpusValidationError(f"top-level aggregate {key} is incorrect")

    family_counts: Counter[str] = Counter()
    version_counts: Counter[str] = Counter()
    for tree in trees:
        family_counts.update(tree.families)
        if tree.reported_versions:
            version_counts.update(tree.reported_versions)
        else:
            version_counts["none"] += 1
    _expect_equal_mapping(
        top,
        "tree_counts_by_family",
        _sorted_counter(family_counts),
        "top-level family counts",
    )
    _expect_equal_mapping(
        top,
        "tree_counts_by_reported_version",
        _sorted_counter(version_counts),
        "top-level version counts",
    )


def _validate_test_policy(
    policy: Mapping[str, Any], *, families: Sequence[str]
) -> Mapping[str, Any]:
    label = "tree test policy"
    status = _require_string(policy, "status", label)
    if status not in {"inventory_only", "correctness"}:
        raise CorpusValidationError("test policy has an unsupported status")
    curation_status = _require_string(policy, "curation_status", label)
    expected_outcome = policy.get("expected_outcome")
    if expected_outcome is not None and (
        not isinstance(expected_outcome, str)
        or expected_outcome not in SUPPORTED_OUTCOMES
    ):
        raise CorpusValidationError("test policy has an unsupported expected outcome")
    schema_hint = policy.get("schema_hint")
    if schema_hint is not None and not isinstance(schema_hint, str):
        raise CorpusValidationError("test policy schema_hint must be a string or null")
    schema_evidence = _require_string_list(policy, "schema_evidence", label)
    if any(not item.strip() for item in schema_evidence):
        raise CorpusValidationError("test policy schema evidence must not be blank")
    _require_string_list(policy, "tags", label)
    generated = _require_bool(
        policy, "expectations_generated_from_current_uncrater", label
    )
    if generated:
        raise CorpusValidationError(
            "expectations generated from the decoder under test are forbidden"
        )

    tiers = policy.get("tiers", [])
    if not isinstance(tiers, list) or any(not isinstance(item, str) for item in tiers):
        raise CorpusValidationError("test policy tiers must be a string list")
    if len(tiers) != len(set(tiers)) or any(
        item not in SUPPORTED_TIERS for item in tiers
    ):
        raise CorpusValidationError("test policy has invalid or duplicate tiers")

    if status == "inventory_only":
        if (
            curation_status != "not_curated"
            or expected_outcome is not None
            or tiers
            or "expectations" in policy
            or "schema_variant" in policy
        ):
            raise CorpusValidationError(
                "inventory-only policy must remain uncurated and expectation-free"
            )
    elif not _policy_is_curated(policy):
        raise CorpusValidationError(
            "non-inventory policy must have reviewed curation and an expected outcome"
        )
    else:
        if not schema_evidence:
            raise CorpusValidationError(
                "curated policy must record independent schema evidence"
            )
        variant = policy.get("schema_variant")
        if variant not in (None, "early", "final"):
            raise CorpusValidationError(
                "test policy schema_variant must be early, final, or null"
            )
        expectations = _require_mapping(
            policy.get("expectations"), "decoder expectations"
        )
        _validate_decoder_expectations(expectations)
        sentinels = expectations["sentinels"]
        if expected_outcome in {"decode", "partial_session"}:
            if not sentinels:
                raise CorpusValidationError(
                    "decoded correctness policies require independent sentinels"
                )
            if not any(
                "value" in sentinel
                and not isinstance(sentinel["value"], (list, Mapping))
                for sentinel in sentinels
            ):
                raise CorpusValidationError(
                    "decoded correctness policies require a scalar value sentinel"
                )
        required_family_sentinels = {
            "zoom": ({"0x270"}, {"AA", "BB", "ABR", "ABI"}),
            "raw_adc_waveform": (
                {
                    "0x2F0",
                    "0x2F1",
                    "0x2F2",
                    "0x2F3",
                    "0x4F0",
                },
                {"waveform"},
            ),
        }
        for family, (appids, attributes) in required_family_sentinels.items():
            if expected_outcome not in {"decode", "partial_session"}:
                continue
            if family not in families:
                continue
            if not any(
                sentinel["appid"] in appids
                and sentinel["attribute"] in attributes
                and (
                    "sha256" in sentinel
                    or sentinel.get("nonzero") is True
                )
                for sentinel in sentinels
            ):
                raise CorpusValidationError(
                    f"{family} correctness policies require a hash or nonzero sentinel"
                )
    return policy


def _policy_is_curated(policy: Mapping[str, Any]) -> bool:
    return (
        policy.get("status") != "inventory_only"
        and policy.get("curation_status") in {"curated", "reviewed"}
        and policy.get("expected_outcome") in SUPPORTED_OUTCOMES
        and policy.get("expectations_generated_from_current_uncrater") is False
    )


def _validate_decoder_expectations(expectations: Mapping[str, Any]) -> None:
    if set(expectations) != DECODER_EXPECTATION_KEYS:
        missing = sorted(DECODER_EXPECTATION_KEYS - set(expectations))
        extra = sorted(set(expectations) - DECODER_EXPECTATION_KEYS)
        raise CorpusValidationError(
            f"decoder expectations have missing keys {missing} and extra keys {extra}"
        )
    for key in (
        "reported_schema_ids",
        "selected_schema_ids",
        "selected_schema_bindings",
    ):
        values = expectations[key]
        if not isinstance(values, list) or any(
            not isinstance(item, str) for item in values
        ):
            raise CorpusValidationError(f"decoder expectation {key} must be a string list")
    if not isinstance(expectations["schema_assumed"], bool):
        raise CorpusValidationError("decoder expectation schema_assumed must be boolean")

    for key in (
        "packet_counts_by_appid",
        "invalid_counts_by_issue",
        "product_counts",
    ):
        values = _require_mapping(expectations[key], f"decoder expectation {key}")
        if any(
            not isinstance(name, str)
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for name, count in values.items()
        ):
            raise CorpusValidationError(
                f"decoder expectation {key} must map strings to nonnegative integers"
            )
    if set(expectations["product_counts"]) != set(_zero_product_counts()):
        raise CorpusValidationError(
            "decoder product-count expectations must name every canonical product"
        )

    shapes = _require_mapping(expectations["shapes"], "decoder expectation shapes")
    if set(shapes) != set(_empty_shapes()):
        raise CorpusValidationError(
            "decoder shape expectations must name every canonical product family"
        )
    associations = _require_mapping(
        expectations["associations"], "decoder expectation associations"
    )
    if set(associations) != set(_empty_associations()):
        raise CorpusValidationError(
            "decoder association expectations must name every canonical group family"
        )
    _validate_json_value(shapes, "decoder shape expectations")
    _validate_json_value(associations, "decoder association expectations")

    sentinels = expectations["sentinels"]
    if not isinstance(sentinels, list):
        raise CorpusValidationError("decoder sentinels must be a list")
    for ordinal, raw_sentinel in enumerate(sentinels):
        sentinel = _require_mapping(raw_sentinel, f"decoder sentinel {ordinal}")
        required = {"packet_index", "appid", "attribute", "index"}
        operators = {"value", "sha256", "nonzero"} & set(sentinel)
        if not required <= set(sentinel) or not operators:
            raise CorpusValidationError(
                "each decoder sentinel needs packet_index, appid, attribute, index, "
                "and at least one value/hash/nonzero assertion"
            )
        if set(sentinel) - required - {"value", "sha256", "nonzero"}:
            raise CorpusValidationError("decoder sentinel has unsupported keys")
        packet_index = sentinel["packet_index"]
        if isinstance(packet_index, bool) or not isinstance(packet_index, int):
            raise CorpusValidationError("decoder sentinel packet_index must be an integer")
        appid = sentinel["appid"]
        if not isinstance(appid, str) or re.fullmatch(r"0x[0-9A-F]{3,4}", appid) is None:
            raise CorpusValidationError("decoder sentinel appid must be canonical hex")
        attribute = sentinel["attribute"]
        if not isinstance(attribute, str) or not attribute:
            raise CorpusValidationError("decoder sentinel attribute must be nonempty")
        indices = sentinel["index"]
        if not isinstance(indices, list) or any(
            isinstance(index, bool) or not isinstance(index, int) for index in indices
        ):
            raise CorpusValidationError("decoder sentinel index must be an integer list")
        if "sha256" in sentinel and (
            not isinstance(sentinel["sha256"], str)
            or SHA256_RE.fullmatch(sentinel["sha256"]) is None
        ):
            raise CorpusValidationError("decoder sentinel SHA-256 is invalid")
        if "nonzero" in sentinel and not isinstance(sentinel["nonzero"], bool):
            raise CorpusValidationError("decoder sentinel nonzero must be boolean")
        if "value" in sentinel:
            _validate_json_value(sentinel["value"], "decoder sentinel value")


def _validate_json_value(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, int, bool)):
        return
    if isinstance(value, float):
        if not np.isfinite(value):
            raise CorpusValidationError(f"{label} must not contain NaN or infinity")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, label)
        return
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CorpusValidationError(f"{label} object keys must be strings")
        for item in value.values():
            _validate_json_value(item, label)
        return
    raise CorpusValidationError(f"{label} is not canonical JSON data")


def _packet_family(appid: int) -> str:
    if appid == 0x209:
        return "hello"
    if appid == 0x206:
        return "housekeeping"
    if appid == 0x20F:
        return "science_metadata"
    if 0x210 <= appid <= 0x23F:
        return "normal_spectrum"
    if 0x240 <= appid <= 0x26F:
        return "time_resolved_spectrum"
    if appid == 0x270:
        return "zoom"
    if appid == 0x280:
        return "calibrator_metadata"
    if 0x281 <= appid <= 0x283:
        return "calibrator_data"
    if 0x284 <= appid <= 0x28B:
        return "calibrator_raw_pfb"
    if 0x28C <= appid <= 0x293:
        return "calibrator_debug"
    if appid == 0x2A0:
        return "grimm"
    if 0x2E0 <= appid <= 0x2E3:
        return "fw_direct_spectrum"
    if 0x2F0 <= appid <= 0x2F3 or appid == 0x4F0:
        return "raw_adc_waveform"
    if appid == 0x2FA:
        return "raw_adc_metadata"
    return "control_or_other"


def _read_hello_version(path: Path) -> str:
    with path.open("rb") as stream:
        prefix = stream.read(4)
    if len(prefix) < 4:
        raise CorpusValidationError("Hello packet is shorter than four bytes")
    return f"0x{int.from_bytes(prefix, 'little'):03X}"


def _resolve_directory_without_symlinks(path: Path, label: str) -> Path:
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        current_stat = _lstat(current, label)
        if stat.S_ISLNK(current_stat.st_mode):
            raise CorpusValidationError(f"{label} must not traverse a symlink")
    final_stat = _lstat(absolute, label)
    if not stat.S_ISDIR(final_stat.st_mode):
        raise CorpusValidationError(f"{label} is not a directory")
    return absolute


def _safe_existing_path(
    root: Path,
    relative: str | PurePosixPath,
    *,
    kind: str,
    label: str,
) -> Path:
    pure = _require_relative_path(str(relative), label)
    current = root
    for part in pure.parts:
        current = current / part
        current_stat = _lstat(current, label)
        if stat.S_ISLNK(current_stat.st_mode):
            raise CorpusValidationError(f"{label} must not traverse a symlink")
    final_stat = current.lstat()
    if kind == "file" and not stat.S_ISREG(final_stat.st_mode):
        raise CorpusValidationError(f"{label} is not a regular file")
    if kind == "directory" and not stat.S_ISDIR(final_stat.st_mode):
        raise CorpusValidationError(f"{label} is not a directory")
    return current


def _require_relative_path(value: str, label: str) -> PurePosixPath:
    if (
        not value
        or "\\" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise CorpusValidationError(f"{label} must be a portable relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
        or (path.parts and path.parts[0].endswith(":"))
    ):
        raise CorpusValidationError(f"{label} must not be absolute or escape its root")
    return path


def _lstat(path: Path, label: str) -> os.stat_result:
    try:
        return path.lstat()
    except FileNotFoundError as exc:
        raise CorpusValidationError(f"missing {label}") from exc


def _load_json_bytes(payload: bytes, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusValidationError(f"{label} is not valid UTF-8 JSON") from exc
    return _require_mapping(value, label)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CorpusValidationError(f"JSON object contains duplicate key {key!r}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise CorpusValidationError(f"JSON contains non-standard constant {value}")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CorpusValidationError(f"{label} must be a JSON object")
    return value


def _require_list(mapping: Mapping[str, Any], key: str, label: str) -> list[Any]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise CorpusValidationError(f"{label} field {key} must be a list")
    return value


def _require_string(mapping: Mapping[str, Any], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise CorpusValidationError(f"{label} field {key} must be a string")
    return value


def _require_string_list(
    mapping: Mapping[str, Any], key: str, label: str
) -> list[str]:
    values = _require_list(mapping, key, label)
    if any(not isinstance(value, str) for value in values):
        raise CorpusValidationError(f"{label} field {key} must contain strings")
    if len(values) != len(set(values)):
        raise CorpusValidationError(f"{label} field {key} contains duplicates")
    return values


def _require_int(mapping: Mapping[str, Any], key: str, label: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CorpusValidationError(
            f"{label} field {key} must be a nonnegative integer"
        )
    return value


def _require_bool(mapping: Mapping[str, Any], key: str, label: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise CorpusValidationError(f"{label} field {key} must be boolean")
    return value


def _require_version(mapping: Mapping[str, Any], key: str, label: str) -> None:
    if _require_int(mapping, key, label) != SUPPORTED_MANIFEST_VERSION:
        raise CorpusValidationError(f"unsupported {label} schema version")


def _require_private_flags(mapping: Mapping[str, Any], label: str) -> None:
    if not _require_bool(mapping, "private_data", label):
        raise CorpusValidationError(f"{label} must be marked private")
    if _require_bool(mapping, "publish_to_public_repository", label):
        raise CorpusValidationError(f"{label} must forbid public publication")


def _expect_equal_list(
    mapping: Mapping[str, Any], key: str, expected: list[Any], label: str
) -> None:
    if mapping.get(key) != expected:
        raise CorpusValidationError(f"{label} do not match the packet inventory")


def _expect_equal_mapping(
    mapping: Mapping[str, Any], key: str, expected: Mapping[str, int], label: str
) -> None:
    actual = _require_count_mapping(mapping, key, label)
    if actual != expected:
        raise CorpusValidationError(f"{label} do not match the packet inventory")


def _require_count_mapping(
    mapping: Mapping[str, Any], key: str, label: str
) -> dict[str, int]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise CorpusValidationError(f"{label} must be a count mapping")
    for count_key, count in value.items():
        if (
            not isinstance(count_key, str)
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
        ):
            raise CorpusValidationError(f"{label} must contain nonnegative integers")
    return value


def _parse_appid(value: str, label: str) -> int:
    if re.fullmatch(r"0x[0-9A-Fa-f]+", value) is None:
        raise CorpusValidationError(f"{label} AppID is not hexadecimal")
    return int(value, 16)


def _format_appid(appid: int) -> str:
    return f"0x{appid:03X}"


def _hex_sort_key(value: str) -> int:
    return int(value, 16)


def _parse_appid_sort_key(value: str) -> int:
    return _parse_appid(value, "observed")


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}
