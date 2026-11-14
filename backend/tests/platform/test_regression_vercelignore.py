"""Regression (worker 23): .vercelignore must not drop the backend runtime.

Defect: worker 07's ``.vercelignore`` had an unanchored ``data/``, which matches
``backend/data/`` too, so the deployed API would have shipped without processor A.
The fix anchored it as ``/data/``. ``deploy_check`` does not test this, so the
rules are evaluated here with ``git check-ignore --no-index`` (gitignore
semantics, which ``.vercelignore`` follows) in a scratch repository.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

MUST_SHIP = [
    "backend/main.py",
    "backend/data/process.py",
    "backend/data/archive.py",
    "backend/routes/frames.py",
    "backend/content/targets.json",
    "backend/content/cases/fair_comparison.json",
    "backend/content/presets/epsilon_indi_b/frames/2026W18_1A_0516_1_D3.json",
    "backend/requirements.txt",
    "frontend/src/main.tsx",
    "frontend/package.json",
    "vercel.json",
]
MUST_IGNORE = [
    "research/build_data/manifest.json",
    "data/raw/x.fits",
    "tools/ingest/ingest.py",
    "backend/tests/api/test_frame.py",
    "backend/content/presets/x/raw.fits",
    "science/reviews/acceptance/check_acceptance.py",
]

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _ignored(rules: str, paths: list[str], tmp: Path) -> set[str]:
    repo = tmp / f"r{abs(hash(rules))}"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text(rules)
    out = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "--no-index", "--stdin"],
        input="\n".join(paths) + "\n",
        capture_output=True,
        text=True,
    )
    assert out.returncode in (0, 1), out.stderr
    return set(out.stdout.split())


def test_vercelignore_keeps_backend_runtime_and_drops_research(tmp_path):
    rules = (REPO / ".vercelignore").read_text()
    for rel in MUST_SHIP[:4]:
        assert (REPO / rel).is_file(), f"fixture path vanished: {rel}"
    ignored = _ignored(rules, MUST_SHIP + MUST_IGNORE, tmp_path)
    assert not ignored & set(MUST_SHIP), f"deployment would drop: {sorted(ignored & set(MUST_SHIP))}"
    assert set(MUST_IGNORE) <= ignored, f"deployment would include: {sorted(set(MUST_IGNORE) - ignored)}"


def test_unanchored_data_rule_is_the_reproduced_defect(tmp_path):
    # Negative control: the original rule really does drop backend/data/.
    ignored = _ignored("data/\n", ["backend/data/process.py"], tmp_path)
    assert ignored == {"backend/data/process.py"}
