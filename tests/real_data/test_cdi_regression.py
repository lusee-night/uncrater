"""Curated private CDI decoder regressions and canonical audit reporting."""

import pytest

from corpus_support import (
    assert_tree_decoder_expectations,
    build_tree_decoder_report,
    canonical_report_bytes,
)


pytestmark = pytest.mark.real_data


def test_curated_tree_decoder_regression(
    cdi_tree, cdi_inventory, cdi_decoder_reports
) -> None:
    report = build_tree_decoder_report(cdi_inventory, cdi_tree)
    assert_tree_decoder_expectations(report, cdi_tree.test_policy)

    if not cdi_decoder_reports:
        repeated = build_tree_decoder_report(cdi_inventory, cdi_tree)
        assert canonical_report_bytes(report) == canonical_report_bytes(repeated)

    cdi_decoder_reports[cdi_tree.tree_id] = report
