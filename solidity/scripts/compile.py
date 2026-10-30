"""Compile all Solidity contracts in this project with solc 0.8.26.

Uses py-solc-x so we don't need solc on the PATH.

Usage:  python scripts/compile.py
Output: prints compile errors if any; zero exit code = all clean.

Sources are discovered recursively under `src/` — new `.sol` files
are picked up automatically.
"""

import os
import sys
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
SOLC_VERSION = "0.8.26"


def discover_sources():
    out = []
    for root, _dirs, files in os.walk(SRC_DIR):
        for name in files:
            if not name.endswith(".sol"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, PROJECT_ROOT).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


def build_source_map(sources):
    out = {}
    for rel in sources:
        abs_path = os.path.join(PROJECT_ROOT, rel)
        with open(abs_path, "r", encoding="utf-8") as f:
            out[rel] = {"content": f.read()}
    return out


def compile_with_solcx():
    try:
        import solcx
    except ImportError:
        print("py-solc-x not installed. Install with: pip install py-solc-x")
        return 1

    from packaging.version import Version
    if Version(SOLC_VERSION) not in solcx.get_installed_solc_versions():
        print(f"Installing solc {SOLC_VERSION}...")
        solcx.install_solc(SOLC_VERSION)
    solcx.set_solc_version(SOLC_VERSION)

    sources = discover_sources()
    if not sources:
        print("No .sol files found under src/.")
        return 1

    input_data = {
        "language": "Solidity",
        "sources": build_source_map(sources),
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
        },
    }
    return process_result(solcx.compile_standard(input_data))


def process_result(data):
    errors = [e for e in data.get("errors", []) if e.get("severity") == "error"]
    warnings = [e for e in data.get("errors", []) if e.get("severity") == "warning"]
    if warnings:
        print("--- warnings (non-fatal) ---")
        for e in warnings:
            print(f"[warning] {e.get('formattedMessage') or e.get('message')}")
    if errors:
        print("--- compile ERRORS ---")
        for e in errors:
            print(f"[error] {e.get('formattedMessage') or e.get('message')}")
        return 1
    contracts = data.get("contracts", {})
    if not contracts:
        print("No contracts in output.")
        return 1
    print("Compile OK. Contracts:")
    for source, names in sorted(contracts.items()):
        for cname, info in sorted(names.items()):
            abi_len = len(info.get("abi", []))
            bytecode = info.get("evm", {}).get("bytecode", {}).get("object", "")
            print(f"  {source}::{cname}  abi={abi_len} entries  bytecode={len(bytecode)//2} bytes")
    return 0


def main():
    try:
        return compile_with_solcx()
    except Exception as e:
        print(f"solcx failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
