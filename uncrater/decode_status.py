"""Machine-readable packet decoding status and typed failures."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class DecodeIssue:
    """One deterministic decoder issue."""

    code: str
    message: str
    appid: int | None = None
    source: str | None = None
    fatal: bool = False
    details: tuple[tuple[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "fatal": self.fatal,
        }
        if self.appid is not None:
            result["appid"] = f"0x{self.appid:03X}"
        if self.source is not None:
            result["source"] = self.source
        if self.details:
            result["details"] = dict(self.details)
        return result


class DecodeStatus:
    """Ordered issue collection shared by every decoded packet."""

    def __init__(self, issues: Iterable[DecodeIssue] = ()):
        self._issues = list(issues)

    @property
    def ok(self) -> bool:
        return not self._issues

    @property
    def issues(self) -> tuple[DecodeIssue, ...]:
        return tuple(self._issues)

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self._issues)

    def has(self, code: str) -> bool:
        return any(issue.code == code for issue in self._issues)

    def add(
        self,
        code: str,
        message: str,
        *,
        appid: int | None = None,
        source: str | None = None,
        fatal: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> DecodeIssue:
        issue = DecodeIssue(
            code=code,
            message=message,
            appid=appid,
            source=source,
            fatal=fatal,
            details=tuple(sorted((details or {}).items())),
        )
        self._issues.append(issue)
        return issue

    def extend(self, issues: Iterable[DecodeIssue]) -> None:
        self._issues.extend(issues)

    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(self.codes).items()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self._issues],
        }


class PacketDecodeError(ValueError):
    """Raised when strict decoding encounters a structural failure."""

    def __init__(self, issue: DecodeIssue, status: DecodeStatus | None = None):
        self.issue = issue
        self.status = status
        context = []
        if issue.appid is not None:
            context.append(f"AppID 0x{issue.appid:03X}")
        if issue.source is not None:
            context.append(issue.source)
        prefix = f" ({', '.join(context)})" if context else ""
        super().__init__(f"{issue.code}{prefix}: {issue.message}")

    @property
    def code(self) -> str:
        return self.issue.code


def source_label(path: str | Path | None) -> str | None:
    """Return a stable filename-only source label."""

    return None if path is None else Path(path).name


__all__ = [
    "DecodeIssue",
    "DecodeStatus",
    "PacketDecodeError",
]
