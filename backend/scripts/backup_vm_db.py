"""
Local Daily Database & State Backup from the Oracle Cloud Hosting VM.

Pulls all production JSON database/state files from the Oracle Cloud VM into
local dated compressed archives (`backend/backups/crypto_bot_db_YYYY-MM-DD.tar.gz`)
plus a `latest/` snapshot and SHA-256 verification manifest, keeping 30 days
of rolling daily backups on this workstation.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_ROOT = ROOT_DIR / "backend" / "backups"
LATEST_DIR = BACKUP_ROOT / "latest"

VM_HOST = os.getenv("CRYPTO_BOT_VM_HOST", "ubuntu@130.210.6.163")
VM_SSH_KEY = os.getenv("CRYPTO_BOT_VM_SSH_KEY", "/Users/swastik/Downloads/ssh-key-2026-11-17.key")
VM_REMOTE_DATA_DIR = "/home/ubuntu/Crypto-Bot/backend/data"
RETENTION_DAYS = int(os.getenv("CRYPTO_BOT_BACKUP_RETENTION_DAYS", "30"))

DB_FILES = [
    "paper_account.json",
    "trade_learnings.json",
    "trade_playbook.json",
    "offline_ml_model.json",
    "latest_analysis_cache.json",
    "recent_consensus_signals.json",
    "telemetry_logs.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_daily_backup() -> dict:
    now_utc = datetime.now(timezone.utc)
    date_tag = now_utc.strftime("%Y-%m-%d")
    ts_tag = now_utc.strftime("%Y-%m-%dT%H-%M-%SZ")

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    staging_dir = BACKUP_ROOT / f"_staging_{ts_tag}"
    staging_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "backup_timestamp_utc": now_utc.isoformat(),
        "date_tag": date_tag,
        "source_host": VM_HOST,
        "source_dir": VM_REMOTE_DATA_DIR,
        "files": {},
        "missing_or_failed": [],
    }

    try:
        for fname in DB_FILES:
            remote_path = f"{VM_HOST}:{VM_REMOTE_DATA_DIR}/{fname}"
            local_path = staging_dir / fname
            res = subprocess.run(
                ["scp", "-o", "StrictHostKeyChecking=no", "-i", VM_SSH_KEY, remote_path, str(local_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if res.returncode != 0 or not local_path.exists():
                manifest["missing_or_failed"].append({"file": fname, "error": res.stderr.strip()})
                continue

            # Verify valid JSON before finalizing backup
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    parsed = json.load(f)
                record_count = None
                if isinstance(parsed, dict) and "trade_history" in parsed:
                    record_count = len(parsed.get("trade_history", []))
                elif isinstance(parsed, dict) and "rules" in parsed:
                    record_count = len(parsed.get("rules", []))
                elif isinstance(parsed, list):
                    record_count = len(parsed)
                manifest["files"][fname] = {
                    "bytes": local_path.stat().st_size,
                    "sha256": _sha256(local_path),
                    "records": record_count,
                }
            except Exception as je:
                manifest["missing_or_failed"].append({"file": fname, "error": f"Invalid JSON: {je}"})

        if not manifest["files"]:
            raise RuntimeError(f"Backup failed: no valid files downloaded from {VM_HOST}")

        manifest_path = staging_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        archive_path = BACKUP_ROOT / f"crypto_bot_db_{date_tag}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in sorted(staging_dir.iterdir()):
                tar.add(item, arcname=item.name)

        if LATEST_DIR.exists():
            shutil.rmtree(LATEST_DIR)
        shutil.copytree(staging_dir, LATEST_DIR)

        # Retention pruning on old daily .tar.gz archives
        archives = sorted(BACKUP_ROOT.glob("crypto_bot_db_*.tar.gz"))
        pruned = []
        if len(archives) > RETENTION_DAYS:
            for old_arch in archives[:-RETENTION_DAYS]:
                old_arch.unlink()
                pruned.append(old_arch.name)

        manifest["archive_path"] = str(archive_path)
        manifest["archive_bytes"] = archive_path.stat().st_size
        manifest["latest_dir"] = str(LATEST_DIR)
        manifest["total_archives_retained"] = len(list(BACKUP_ROOT.glob("crypto_bot_db_*.tar.gz")))
        manifest["pruned_archives"] = pruned
        return manifest
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


if __name__ == "__main__":
    summary = run_daily_backup()
    print(json.dumps(summary, indent=2))
    if summary.get("missing_or_failed"):
        sys.exit(1)
