"""Pytest configuration for optional private CDI regression data."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_support import (
    CORPUS_ENV,
    SUPPORTED_TIERS,
    CorpusConfig,
    CorpusError,
    ValidatedCorpus,
    build_decoder_audit_report,
    config_from_sources,
    select_correctness_trees,
    validate_corpus,
    write_report,
)


CONFIG_ATTR = "_uncrater_cdi_config"
CORPUS_ATTR = "_uncrater_validated_corpus"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("uncrater private CDI corpus")
    group.addoption(
        "--require-cdi-corpus",
        action="store_true",
        default=False,
        help=f"fail the session if {CORPUS_ENV} is unset",
    )
    group.addoption(
        "--cdi-tier",
        choices=SUPPORTED_TIERS,
        default=None,
        help="private CDI correctness tier (default: full when configured)",
    )
    group.addoption(
        "--cdi-report-dir",
        default=None,
        metavar="PATH",
        help="explicit private report directory outside the corpus root",
    )


def pytest_configure(config: pytest.Config) -> None:
    try:
        corpus_config = config_from_sources(
            cli_tier=config.getoption("--cdi-tier"),
            require=config.getoption("--require-cdi-corpus"),
            report_dir=config.getoption("--cdi-report-dir"),
        )
        corpus = (
            validate_corpus(corpus_config.root, verify_hashes=True)
            if corpus_config.root is not None
            else None
        )
    except CorpusError as exc:
        raise pytest.UsageError(str(exc)) from exc
    setattr(config, CONFIG_ATTR, corpus_config)
    if corpus is not None:
        setattr(config, CORPUS_ATTR, corpus)


def pytest_ignore_collect(collection_path, config: pytest.Config) -> bool | None:
    """Leave one clear skip when the optional corpus is not configured."""

    path = Path(str(collection_path))
    corpus_config = get_corpus_config(config)
    if (
        corpus_config.root is None
        and path.name == "test_cdi_regression.py"
        and path.parent.name == "real_data"
    ):
        return True
    return None


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "cdi_tree" not in metafunc.fixturenames:
        return
    corpus_config = get_corpus_config(metafunc.config)
    if corpus_config.root is None:
        metafunc.parametrize(
            "cdi_tree",
            [
                pytest.param(
                    None,
                    marks=pytest.mark.skip(
                        reason=f"{CORPUS_ENV} is unset; private real-data regression is optional"
                    ),
                )
            ],
        )
        return
    try:
        corpus = get_validated_corpus(metafunc.config)
        trees = select_correctness_trees(corpus, corpus_config.tier)
    except CorpusError as exc:
        raise pytest.UsageError(str(exc)) from exc
    metafunc.parametrize("cdi_tree", trees, ids=[tree.tree_id for tree in trees])


def get_corpus_config(config: pytest.Config) -> CorpusConfig:
    corpus_config = getattr(config, CONFIG_ATTR, None)
    if corpus_config is None:
        corpus_config = config_from_sources()
        setattr(config, CONFIG_ATTR, corpus_config)
    return corpus_config


def get_validated_corpus(config: pytest.Config) -> ValidatedCorpus:
    cached = getattr(config, CORPUS_ATTR, None)
    if cached is not None:
        return cached
    corpus_config = get_corpus_config(config)
    if corpus_config.root is None:
        raise CorpusError(f"{CORPUS_ENV} is unset")
    corpus = validate_corpus(corpus_config.root, verify_hashes=True)
    setattr(config, CORPUS_ATTR, corpus)
    return corpus


@pytest.fixture(scope="session")
def cdi_corpus_config(pytestconfig: pytest.Config) -> CorpusConfig:
    return get_corpus_config(pytestconfig)


@pytest.fixture(scope="session")
def cdi_inventory(pytestconfig: pytest.Config) -> ValidatedCorpus:
    corpus_config = get_corpus_config(pytestconfig)
    if corpus_config.root is None:
        pytest.skip(
            f"{CORPUS_ENV} is unset; private real-data regression is optional"
        )
    try:
        return get_validated_corpus(pytestconfig)
    except CorpusError as exc:
        pytest.fail(str(exc), pytrace=False)


@pytest.fixture(scope="session")
def cdi_decoder_reports(
    pytestconfig: pytest.Config,
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, dict]:
    """Collect passing per-tree reports and emit one complete canonical audit."""

    reports: dict[str, dict] = {}
    yield reports
    corpus_config = get_corpus_config(pytestconfig)
    if corpus_config.root is None:
        return
    corpus = get_validated_corpus(pytestconfig)
    selected = select_correctness_trees(corpus, corpus_config.tier)
    expected_ids = {tree.tree_id for tree in selected}
    if set(reports) != expected_ids:
        return
    audit = build_decoder_audit_report(
        corpus,
        corpus_config.tier,
        [reports[tree_id] for tree_id in sorted(reports)],
    )
    report_dir = corpus_config.report_dir or tmp_path_factory.mktemp("cdi-audit")
    write_report(
        audit,
        report_dir / "uncrater-cdi-decoder-audit.json",
        corpus_root=corpus.root,
    )
