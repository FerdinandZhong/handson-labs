#!/usr/bin/env python3
"""
Deploy Synthetic Data Pipeline as a CAI Application.

Run as a CAI Job. Creates or updates the application via CDSW API v2.

Environment variables (forwarded into the Application):
  # Impala (pipeline and agent scan)
  IMPALA_HOST, IMPALA_USER, IMPALA_PASS, IMPALA_DB

  # Deterministic pipeline mode (/pipeline/*)
  TARGET_TABLES, ROWS, SEED
  MANIFEST_PATH, OUTPUT_DIR, REPORT_PATH
  PIPELINE_DIR — path to synthetic_data_workflow_d3 (default: sibling folder)

  # Agentic mode (/agent/*) — CrewAI LLM (OpenAI-compatible API)
  LLM_API_BASE_URL — chat-completions base URL (e.g. https://api.openai.com/v1)
  LLM_API_KEY      — API key for the LLM endpoint
  LLM_MODEL        — model ID (default: gpt-4o)
  # Deprecated aliases (still read): CAI_BASE_URL, CAI_URL, CAI_API_KEY, CAI_MODEL

  # CML Job dispatch (used by CmlJobTool inside the crew)
  CAI_WORKBENCH_HOST        — Workbench URL for Job creation
  CAI_WORKBENCH_API_KEY     — Workbench API key (defaults to CDSW_APIV2_KEY)
  CDSW_PROJECT_ID           — Project ID for CmlJobTool (auto-set on CAI; optional override)
  OUTPUT_SCRIPTS_DIR        — where Agent 4 writes generated scripts

  app_suffix — optional side-by-side deploy suffix
"""

import os
import sys

import requests
import urllib3

BASE_APP_NAME = "Synthetic Data Pipeline"
PROJECT_ROOT = "/home/cdsw"
DEFAULT_APP_SCRIPT = f"{PROJECT_ROOT}/synthetic_data_app/run_app.py"
DEFAULT_APP_DIR = f"{PROJECT_ROOT}/synthetic_data_app"
DEFAULT_PIPELINE_DIR = f"{PROJECT_ROOT}/synthetic_data_workflow_d3"
RUNTIME_IMAGE = (
    "docker.repository.cloudera.com/cloudera/cdsw/"
    "ml-runtime-pbj-jupyterlab-python3.11-standard:2026.04.1-b7"
)


def get_app_name() -> str:
    suffix = os.environ.get("app_suffix", "").strip()
    return f"{BASE_APP_NAME} - {suffix}" if suffix else BASE_APP_NAME


def get_subdomain(project_id: str) -> str:
    suffix = os.environ.get("app_suffix", "").strip()
    base = f"synthetic-data-{project_id.lower()}"
    return f"synthetic-data-{suffix.lower()}-{project_id.lower()}" if suffix else base


def get_app_script() -> str:
    return os.environ.get("APP_SCRIPT", DEFAULT_APP_SCRIPT).strip()


def validate_app_script() -> str:
    script = get_app_script()
    if script.startswith("/"):
        script_path = script
    else:
        script_path = os.path.join(os.environ.get("CDSW_PROJECT_ROOT", PROJECT_ROOT), script)
    if not os.path.isfile(script_path):
        print(f"Error: Startup script not found: {script_path}")
        print(f"  Expected: {DEFAULT_APP_SCRIPT}")
        sys.exit(1)
    return script


def build_app_env(project_id: str = "", domain: str = "") -> dict:
    dom = (
        os.environ.get("CAI_WORKBENCH_HOST")
        or os.environ.get("CDSW_DOMAIN")
        or domain
    )
    if dom and not dom.startswith(("http://", "https://")):
        dom = f"https://{dom}"

    env = {
        "app_suffix": os.environ.get("app_suffix", "default"),
        "APP_DIR": os.environ.get("APP_DIR", DEFAULT_APP_DIR),
        "PIPELINE_DIR": os.environ.get("PIPELINE_DIR", DEFAULT_PIPELINE_DIR),
        # Auto-inject CML Job dispatch credentials from the deploy Job context
        "CAI_WORKBENCH_HOST": dom,
        "CAI_WORKBENCH_API_KEY": (
            os.environ.get("CAI_WORKBENCH_API_KEY") or os.environ.get("CDSW_APIV2_KEY", "")
        ),
        "CDSW_PROJECT_ID": os.environ.get("CDSW_PROJECT_ID") or project_id,
    }
    for key in (
        # Impala
        "IMPALA_HOST", "IMPALA_USER", "IMPALA_PASS", "IMPALA_DB",
        # Deterministic pipeline mode
        "TARGET_TABLES", "ROWS", "SEED",
        "MANIFEST_PATH", "OUTPUT_DIR", "REPORT_PATH", "PIPELINE_DIR",
        # Agentic mode — LLM (OpenAI-compatible)
        "LLM_API_BASE_URL", "LLM_API_KEY", "LLM_MODEL",
        "CAI_BASE_URL", "CAI_URL", "CAI_API_KEY", "CAI_MODEL",  # deprecated aliases
        # Agentic mode — CML Job dispatch
        "CAI_WORKBENCH_HOST", "CAI_WORKBENCH_API_KEY", "CDSW_PROJECT_ID",
        "CAI_WORKBENCH_PROJECT_ID",  # deprecated alias
        "OUTPUT_SCRIPTS_DIR",
    ):
        val = os.environ.get(key, "")
        if val:
            env[key] = val
    return env


def deploy_application(client: requests.Session, domain: str, project_id: str) -> dict:
    app_name = get_app_name()
    subdomain = get_subdomain(project_id)
    apps_url = f"{domain}/api/v2/projects/{project_id}/applications"
    app_script = validate_app_script()

    app_config = {
        "name": app_name,
        "description": "D3 synthetic data pipeline — deterministic (/pipeline/*) + agentic CrewAI (/agent/*)",
        "subdomain": subdomain,
        "script": app_script,
        "kernel": "python3",
        "cpu": 4,
        "memory": 8,
        "bypass_authentication": True,
        "runtime_identifier": RUNTIME_IMAGE,
        "environment": build_app_env(project_id=project_id, domain=domain),
    }

    response = client.get(apps_url)
    response.raise_for_status()

    existing_app = None
    for app in response.json().get("applications", []):
        if app.get("name") == app_name:
            existing_app = app
            break

    if existing_app:
        app_id = existing_app["id"]
        print(f"Updating existing application: {app_id}")
        client.patch(f"{apps_url}/{app_id}", json=app_config).raise_for_status()
        client.post(f"{apps_url}/{app_id}/restart").raise_for_status()
        print("Application updated and restarted.")
        return existing_app

    print("Creating new application...")
    response = client.post(apps_url, json=app_config)
    response.raise_for_status()
    created = response.json()
    print(f"Application created: {created.get('id')}")
    return created


def main() -> None:
    print("=" * 60)
    print("  Deploy Synthetic Data Pipeline as CAI Application")
    print("=" * 60)

    api_key = os.environ.get("CDSW_APIV2_KEY")
    domain = os.environ.get("CDSW_DOMAIN")
    project_id = os.environ.get("CDSW_PROJECT_ID")

    if not all([api_key, domain, project_id]):
        print("Error: Must run inside CAI (CDSW_APIV2_KEY, CDSW_DOMAIN, CDSW_PROJECT_ID required)")
        sys.exit(1)

    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    print(f"Domain     : {domain}")
    print(f"Project ID : {project_id}")
    print(f"App Name   : {get_app_name()}")
    print(f"App Script : {get_app_script()}")
    print(f"Subdomain  : {get_subdomain(project_id)}")
    print()

    client = requests.Session()
    client.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    client.trust_env = False
    client.verify = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        deploy_application(client, domain, project_id)
        subdomain = get_subdomain(project_id)
        print()
        print("=" * 60)
        print("  Deployment Complete!")
        print("=" * 60)
        print(f"Application URL : {domain}/{subdomain}")
        print()
        print("POST /pipeline/all to run the full pipeline:")
        print(f'  curl -X POST {domain}/{subdomain}/pipeline/all \\')
        print('       -H "Content-Type: application/json" \\')
        print('       -d \'{"target_tables": "eda_bwc_cfmast_d_sg,eda_bwc_cfacct_d_sg,eda_rbk_tltx_d", "rows": 1000}\'')
    except requests.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(f"Response  : {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
