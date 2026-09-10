"""Read-only inventory validation for an explicitly configured CDI corpus."""

from pathlib import Path

import pytest

from corpus_support import (
    build_inventory_report,
    canonical_report_bytes,
    write_report,
)


pytestmark = pytest.mark.real_data


def test_private_corpus_inventory(
    cdi_inventory, cdi_corpus_config, tmp_path: Path
) -> None:
    report = build_inventory_report(cdi_inventory, detailed=True)
    payload = canonical_report_bytes(report)
    assert str(cdi_inventory.root).encode() not in payload
    assert len(report["trees"]) == len(cdi_inventory.trees)

    report_dir = cdi_corpus_config.report_dir or tmp_path
    output = write_report(
        report,
        report_dir / "uncrater-cdi-inventory.json",
        corpus_root=cdi_inventory.root,
    )
    assert output.read_bytes() == payload
