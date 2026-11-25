"""
Local-Only Offline ML Training, Numba Backtesting & VM Artifact Sync.

Ensures heavy Numba/ML training and backtesting execute strictly on the local
workstation rather than the resource-constrained Oracle Cloud VM, while keeping
the hosting VM's inference model (`offline_ml_model.json`) updated daily from
live VM trade history and AI learnings.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.services.offline_ml_engine import DATA_DIR, MODEL_FILE, offline_ml_engine

VM_HOST = os.getenv("CRYPTO_BOT_VM_HOST", "ubuntu@130.210.6.163")
VM_SSH_KEY = os.getenv("CRYPTO_BOT_VM_SSH_KEY", "/Users/swastik/Downloads/ssh-key-2026-11-17.key")
VM_REMOTE_DATA_DIR = "/home/ubuntu/Crypto-Bot/backend/data"
VM_SYNC_DIR = DATA_DIR / "vm_sync"


def _ssh_base() -> list:
    return ["scp", "-o", "StrictHostKeyChecking=no", "-i", VM_SSH_KEY]


def sync_trade_knowledge_from_vm() -> Path:
    """Download latest trade history & AI learnings from the hosting VM."""
    VM_SYNC_DIR.mkdir(parents=True, exist_ok=True)
    files = ["paper_account.json", "trade_learnings.json", "trade_playbook.json"]
    for fname in files:
        remote = f"{VM_HOST}:{VM_REMOTE_DATA_DIR}/{fname}"
        local = str(VM_SYNC_DIR / fname)
        res = subprocess.run(_ssh_base() + [remote, local], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[LocalMLSync Notice] Could not pull {fname} cleanly: {res.stderr.strip()}")
        else:
            print(f"[LocalMLSync] Pulled live {fname} from VM -> {local}")
    return VM_SYNC_DIR


def push_model_to_vm() -> None:
    """Upload locally validated & promoted offline_ml_model.json to the hosting VM."""
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Trained model artifact missing: {MODEL_FILE}")
    remote = f"{VM_HOST}:{VM_REMOTE_DATA_DIR}/offline_ml_model.json"
    res = subprocess.run(_ssh_base() + [str(MODEL_FILE), remote], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"SCP upload to VM failed: {res.stderr.strip()}")
    print(f"[LocalMLSync] Uploaded promoted model artifact to VM ({remote}).")


async def run_local_train_and_sync(force: bool = True, push_if_promoted: bool = True) -> dict:
    sync_dir = sync_trade_knowledge_from_vm()
    use_dir = sync_dir if (sync_dir / "paper_account.json").exists() else None
    result = await offline_ml_engine.train_and_backtest_daily(force=force, source_data_dir=use_dir)
    print(json.dumps(result, indent=2))
    if push_if_promoted and result.get("promoted"):
        push_model_to_vm()
    return result


if __name__ == "__main__":
    asyncio.run(run_local_train_and_sync(force=True, push_if_promoted=True))
