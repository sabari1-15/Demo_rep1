"""
Appian Deploy Tool
==================
Full deployment pipeline for a target Appian environment:

  Step 1  – Pick a .zip package file to deploy
  Step 2  – Inspect the package     (POST /inspections)
  Step 3  – Poll inspection results  (GET  /inspections/<uuid>)
  Step 4  – Show errors/warnings; ask user to confirm
  Step 5  – Deploy the package       (POST /deployments, Action-Type: import)
  Step 6  – Poll deployment status   (GET  /deployments/<uuid>)
  Step 7  – Print final summary + log

References (Appian 26.2):
  https://docs.appian.com/suite/help/26.2/Inspect_Package_API.html
  https://docs.appian.com/suite/help/26.2/Export_Package_API.html
  https://docs.appian.com/suite/help/26.2/Get_Deployment_Results_API.html
"""

import os
import sys
import time
import json
import glob
import requests
from pathlib import Path
from dotenv import load_dotenv
from requests_toolbelt import MultipartEncoder

# ─────────────────────────────────────────────
# Load .env
# ─────────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if not _env_path.exists():
    _env_path = Path.cwd() / ".env"

if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
    print(f"[✓] Loaded config from: {_env_path}")
else:
    load_dotenv()
    print("[i] No .env found next to script — using system environment variables.")

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
TARGET_DOMAIN  = os.getenv("TARGET_APPIAN_DOMAIN",  "")
TARGET_API_KEY = os.getenv("TARGET_APPIAN_API_KEY", "")
PACKAGE_DIR    = os.getenv("APPIAN_DOWNLOAD_DIR",   ".")
POLL_INTERVAL  = int(os.getenv("APPIAN_POLL_INTERVAL",  "5"))
MAX_POLL_TRIES = int(os.getenv("APPIAN_MAX_POLL_TRIES", "60"))

BASE_URL       = f"https://{TARGET_DOMAIN}/suite/deployment-management/v2"

# ─────────────────────────────────────────────
# Shared session
# ─────────────────────────────────────────────
session = requests.Session()
session.headers.update({"appian-api-key": TARGET_API_KEY})


# ══════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════

def _divider(char="─", width=65):
    print(char * width)


def _section(title: str):
    _divider()
    print(f"  {title}")
    _divider()


def _handle_api_error(resp: requests.Response, context: str = "API call"):
    """
    Parse and print the full Appian error response body in a readable way.
    Exits the script cleanly without showing a raw Python traceback.
    """
    print(f"\n{'─' * 65}")
    print(f"  ✗  {context} failed")
    print(f"     Status : {resp.status_code} {resp.reason}")
    print(f"     URL    : {resp.url}")
    print(f"\n  ── Appian Response ────────────────────────────────────────")

    try:
        body = resp.json()
        print(json.dumps(body, indent=4))

        # Surface known Appian error fields prominently
        for key in ("errors", "message", "errorMessage", "error", "details"):
            if key in body:
                print(f"\n  ⚠  [{key}]: {body[key]}")
    except ValueError:
        print(resp.text or "  (empty response body)")

    print(f"{'─' * 65}\n")
    sys.exit(1)


def _safe_get(url: str, context: str, **kwargs) -> requests.Response:
    """GET with clean error handling — no raw tracebacks."""
    try:
        resp = session.get(url, timeout=30, **kwargs)
        if not resp.ok:
            _handle_api_error(resp, context)
        return resp
    except requests.exceptions.ConnectionError:
        print(f"\n  ✗  Connection failed. Check TARGET_APPIAN_DOMAIN in your .env")
        print(f"     URL: {url}\n")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"\n  ✗  Request timed out for: {url}\n")
        sys.exit(1)


def _safe_post(url: str, context: str, **kwargs) -> requests.Response:
    """POST with clean error handling — no raw tracebacks."""
    try:
        resp = session.post(url, timeout=120, **kwargs)
        if not resp.ok:
            _handle_api_error(resp, context)
        return resp
    except requests.exceptions.ConnectionError:
        print(f"\n  ✗  Connection failed. Check TARGET_APPIAN_DOMAIN in your .env")
        print(f"     URL: {url}\n")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"\n  ✗  Request timed out for: {url}\n")
        sys.exit(1)


def _poll(label: str, url: str) -> dict:
    """Poll until status leaves IN_PROGRESS. Returns final response dict."""
    print(f"\n[…] Polling {label} every {POLL_INTERVAL}s …")
    for attempt in range(1, MAX_POLL_TRIES + 1):
        resp   = _safe_get(url, f"Poll {label}")
        data   = resp.json()
        status = data.get("status", "UNKNOWN")
        print(f"    Attempt {attempt:>3}/{MAX_POLL_TRIES} — {status}")
        if status != "IN_PROGRESS":
            return data
        time.sleep(POLL_INTERVAL)

    print(f"\n  ✗  {label} did not finish after {MAX_POLL_TRIES * POLL_INTERVAL}s. "
          "Check Appian Designer → Deploy view.\n")
    sys.exit(1)


# ══════════════════════════════════════════════
# Step 1 – Choose a .zip file
# ══════════════════════════════════════════════

def pick_zip_file() -> str:
    _section("STEP 1 — Select a package .zip file to deploy")

    zips = sorted(glob.glob(os.path.join(PACKAGE_DIR, "*.zip")))
    if not zips:
        print(f"  ⚠  No .zip files found in: {os.path.abspath(PACKAGE_DIR)}")
        print("     Set APPIAN_DOWNLOAD_DIR in your .env to the correct folder.")
        sys.exit(1)

    for idx, path in enumerate(zips, start=1):
        size_kb = os.path.getsize(path) / 1024
        print(f"  {idx:>3}.  {os.path.basename(path)}  ({size_kb:,.1f} KB)")

    _divider()
    while True:
        raw = input(f"\nEnter file number [1–{len(zips)}] (or 'q' to quit): ").strip()
        if raw.lower() in ("q", "quit"):
            print("Aborted.")
            sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(zips):
            chosen = zips[int(raw) - 1]
            print(f"\n[✓] Selected: {os.path.basename(chosen)}\n")
            return chosen
        print(f"  ⚠  Enter a number between 1 and {len(zips)}.")


# ══════════════════════════════════════════════
# Step 2 – Inspect
# ══════════════════════════════════════════════

def inspect_package(zip_path: str) -> dict:
    _section("STEP 2 — Inspect package on target environment")

    url          = f"{BASE_URL}/inspections"
    package_name = os.path.basename(zip_path)

    # Per Appian docs:
    #   - "packageFileName" must match the filename of the uploaded zip
    #   - The multipart form field key for the file can be anything (we use "package")
    payload = {"packageFileName": package_name}

    print(f"[→] Uploading {package_name} for inspection …\n")
    print(f"[i] Payload: {json.dumps(payload, indent=4)}\n")

    with open(zip_path, "rb") as zf:
        multipart = MultipartEncoder(fields={
            "json":    json.dumps(payload),
            "package": (package_name, zf, "application/zip"),
        })
        resp = _safe_post(
            url, "Inspect package",
            headers={"Content-Type": multipart.content_type},
            data=multipart,
        )

    result = resp.json()
    print(f"[✓] Inspection triggered.  UUID: {result.get('uuid')}")
    return result


# ══════════════════════════════════════════════
# Step 3 – Poll inspection
# ══════════════════════════════════════════════

def poll_inspection(inspection_uuid: str) -> dict:
    url = f"{BASE_URL}/inspections/{inspection_uuid}"
    return _poll("Inspection", url)


# ══════════════════════════════════════════════
# Step 4 – Show inspection results & confirm
# ══════════════════════════════════════════════

def display_inspection_results(result: dict) -> bool:
    _section("STEP 3 — Inspection Results")

    status   = result.get("status", "UNKNOWN")
    errors   = result.get("errors",   [])
    warnings = result.get("warnings", [])

    print(f"  Overall status : {status}")
    print(f"  Errors         : {len(errors)}")
    print(f"  Warnings       : {len(warnings)}\n")

    if errors:
        print("  ── ERRORS (will block deployment) ──────────────────────────")
        for i, err in enumerate(errors, 1):
            obj   = err.get("objectName", err.get("name", "—"))
            msg   = err.get("message", str(err))
            etype = err.get("type", "")
            print(f"  {i:>3}. [{etype}] {obj}")
            print(f"       {msg}")
        print()

    if warnings:
        print("  ── WARNINGS (deployment can still proceed) ─────────────────")
        for i, w in enumerate(warnings, 1):
            obj   = w.get("objectName", w.get("name", "—"))
            msg   = w.get("message", str(w))
            wtype = w.get("type", "")
            print(f"  {i:>3}. [{wtype}] {obj}")
            print(f"       {msg}")
        print()

    if not errors and not warnings:
        print("  ✅  No errors or warnings — package is clean.\n")

    if errors:
        print("  ❌  Inspection found ERRORS. Deployment is not recommended.")
        return input("  Proceed anyway? (yes/no): ").strip().lower() in ("yes", "y")

    if warnings:
        return input("  Warnings found. Proceed with deployment? (yes/no): ").strip().lower() in ("yes", "y")

    return True


# ══════════════════════════════════════════════
# Step 5 – Deploy
# ══════════════════════════════════════════════

def deploy_package(zip_path: str) -> dict:
    _section("STEP 4 — Deploy package to target environment")

    url          = f"{BASE_URL}/deployments"
    package_name = os.path.basename(zip_path)

    # Per Appian docs:
    #   - "name" is REQUIRED in the JSON body
    #   - "packageFileName" must match the filename of the uploaded zip
    #   - The multipart form field key for the file can be anything (we use "package")
    deploy_name = package_name[:-4] if package_name.lower().endswith(".zip") else package_name
    payload = {
        "name":            deploy_name,
        "description":     "Deployed via appian_deploy.py",
        "packageFileName": package_name,
    }

    print(f"[→] Uploading {package_name} for import …\n")
    print(f"[i] Payload: {json.dumps(payload, indent=4)}\n")

    with open(zip_path, "rb") as zf:
        multipart = MultipartEncoder(fields={
            "json":    json.dumps(payload),
            "package": (package_name, zf, "application/zip"),
        })
        resp = _safe_post(
            url, "Deploy package",
            headers={"Action-Type": "import", "Content-Type": multipart.content_type},
            data=multipart,
        )

    result = resp.json()
    print(f"[✓] Deployment triggered.  UUID: {result.get('uuid')}")
    print(f"    Status: {result.get('status')}\n")
    return result


# ══════════════════════════════════════════════
# Step 6 – Poll deployment
# ══════════════════════════════════════════════

def poll_deployment(deployment_uuid: str) -> dict:
    url = f"{BASE_URL}/deployments/{deployment_uuid}"
    return _poll("Deployment", url)


# ══════════════════════════════════════════════
# Step 7 – Final summary
# ══════════════════════════════════════════════

def print_deployment_summary(result: dict):
    _section("STEP 5 — Deployment Summary")

    status     = result.get("status", "UNKNOWN")
    uuid       = result.get("uuid",   "—")
    deploy_url = result.get("url",    "—")
    errors     = result.get("errors",   [])
    warnings   = result.get("warnings", [])
    log        = result.get("log",      [])

    icon = {"COMPLETED": "✅", "COMPLETED_WITH_ERRORS": "⚠️ ", "FAILED": "❌"}.get(status, "❓")

    print(f"  {icon}  Status         : {status}")
    print(f"       UUID           : {uuid}")
    print(f"       Deployment URL : {deploy_url}")
    print(f"       Errors         : {len(errors)}")
    print(f"       Warnings       : {len(warnings)}\n")

    if errors:
        print("  ── DEPLOYMENT ERRORS ───────────────────────────────────────")
        for i, err in enumerate(errors, 1):
            print(f"  {i:>3}. {err.get('objectName', err.get('name','—'))}")
            print(f"       {err.get('message', str(err))}")
        print()

    if warnings:
        print("  ── DEPLOYMENT WARNINGS ─────────────────────────────────────")
        for i, w in enumerate(warnings, 1):
            print(f"  {i:>3}. {w.get('objectName', w.get('name','—'))}")
            print(f"       {w.get('message', str(w))}")
        print()

    if log:
        print("  ── DEPLOYMENT LOG ──────────────────────────────────────────")
        for entry in log:
            ts  = entry.get("timestamp", "")
            lvl = entry.get("level", "INFO")
            msg = entry.get("message", str(entry))
            print(f"  [{ts}] [{lvl}] {msg}")
        print()

    _divider("═")
    if status == "COMPLETED":
        print("  🎉  Deployment completed successfully!")
    elif status == "COMPLETED_WITH_ERRORS":
        print("  ⚠️   Deployment completed with errors. Review above and check Appian Designer.")
    else:
        print("  ❌  Deployment FAILED. Check the Deploy view in Appian Designer.")
    _divider("═")


# ══════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════

def main():
    missing = [k for k, v in {
        "TARGET_APPIAN_DOMAIN":  TARGET_DOMAIN,
        "TARGET_APPIAN_API_KEY": TARGET_API_KEY,
    }.items() if not v]

    if missing:
        print(
            "\n⚠  Missing required configuration values:\n"
            + "".join(f"   • {k}\n" for k in missing)
            + "\n   Add them to your .env file (see .env.example).\n"
        )
        sys.exit(1)

    print("\n" + "═" * 65)
    print(f"  APPIAN DEPLOY TOOL  —  Target: {TARGET_DOMAIN}")
    print("═" * 65)

    try:
        zip_path = pick_zip_file()

        inspection = inspect_package(zip_path)
        inspection_uuid = inspection.get("uuid")
        if not inspection_uuid:
            print(f"\n  ✗  Inspection response did not return a UUID.\n"
                  f"     Full response: {json.dumps(inspection, indent=2)}\n")
            sys.exit(1)

        inspection_result = poll_inspection(inspection_uuid)

        if not display_inspection_results(inspection_result):
            print("\n[!] Deployment cancelled by user.\n")
            sys.exit(0)

        deployment = deploy_package(zip_path)
        deployment_uuid = deployment.get("uuid")
        if not deployment_uuid:
            print(f"\n  ✗  Deployment response did not return a UUID.\n"
                  f"     Full response: {json.dumps(deployment, indent=2)}\n")
            sys.exit(1)

        deployment_result = poll_deployment(deployment_uuid)
        print_deployment_summary(deployment_result)

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user. Exiting.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ✗  Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
