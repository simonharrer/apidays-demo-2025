#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml",
#     "requests",
# ]
# ///
"""
Upload business definitions and data contract to Entropy Data.

Usage:
    uv run upload_to_entropy.py

Environment variables:
    ENTROPY_API_KEY: API key for Entropy Data (required)
    ENTROPY_BASE_URL: Base URL for Entropy Data API (default: https://entropydata.datamesh-manager.com)
"""

import os
import sys
from pathlib import Path

import yaml
import requests


def get_config():
    """Get configuration from environment variables."""
    api_key = os.environ.get("ENTROPY_API_KEY")
    if not api_key:
        print("Error: ENTROPY_API_KEY environment variable is required")
        sys.exit(1)

    base_url = os.environ.get("ENTROPY_BASE_URL", "https://entropydata.datamesh-manager.com")
    return api_key, base_url


def load_yaml_file(file_path: Path) -> dict:
    """Load a YAML file and return as dict."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def transform_definition_urls(obj, base_url: str, org_slug: str):
    """Recursively transform file:// URLs to Entropy Data definition URLs."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "url" and isinstance(value, str) and value.startswith("file://business-definitions/"):
                # Extract the definition ID from the file path
                # e.g., "file://business-definitions/order/order_id.yaml" -> "order/order_id"
                definition_id = value.replace("file://business-definitions/", "").replace(".yaml", "")
                # Handle the rename from global to technical
                definition_id = definition_id.replace("global/", "technical/")
                obj[key] = f"{base_url}/{org_slug}/definitions/{definition_id}"
            else:
                transform_definition_urls(value, base_url, org_slug)
    elif isinstance(obj, list):
        for item in obj:
            transform_definition_urls(item, base_url, org_slug)


def create_team(api_key: str, base_url: str, team_id: str) -> bool:
    """Create a team with minimal data if it doesn't exist."""
    url = f"{base_url}/api/teams/{team_id}"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    # Create minimal team payload with default owner
    team = {
        "id": team_id,
        "name": team_id.replace("-", " ").title(),
        "type": "Team",
        "members": [
            {
                "emailAddress": "simon.harrer@entropy-data.com",
                "role": "owner"
            }
        ]
    }

    response = requests.put(url, headers=headers, json=team)

    if response.status_code == 200:
        print(f"  ✓ Created/updated team: {team_id}")
        return True
    else:
        print(f"  ✗ Failed to create team {team_id}: {response.status_code} - {response.text}")
        return False


def upload_definition(api_key: str, base_url: str, definition: dict) -> bool:
    """Upload a single definition to Entropy Data."""
    definition_id = definition.get("id")
    if not definition_id:
        print(f"  Error: Definition missing 'id' field")
        return False

    # URL encode the ID (handles slashes in IDs like "order/order_id")
    encoded_id = requests.utils.quote(definition_id, safe="")
    url = f"{base_url}/api/definitions/{encoded_id}"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.put(url, headers=headers, json=definition)

    if response.status_code == 200:
        print(f"  ✓ Uploaded definition: {definition_id}")
        return True
    else:
        print(f"  ✗ Failed to upload {definition_id}: {response.status_code} - {response.text}")
        return False


def upload_data_contract(api_key: str, base_url: str, contract: dict) -> bool:
    """Upload a data contract to Entropy Data."""
    contract_id = contract.get("id")
    if not contract_id:
        print(f"  Error: Data contract missing 'id' field")
        return False

    url = f"{base_url}/api/datacontracts/{contract_id}"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.put(url, headers=headers, json=contract)

    if response.status_code == 200:
        print(f"  ✓ Uploaded data contract: {contract_id}")
        return True
    else:
        print(f"  ✗ Failed to upload data contract {contract_id}: {response.status_code} - {response.text}")
        return False


def main():
    api_key, base_url = get_config()
    project_root = Path(__file__).parent

    print(f"Uploading to Entropy Data: {base_url}")
    print()

    # Load all definitions first
    definitions_dir = project_root / "business-definitions"
    definition_files = list(definitions_dir.rglob("*.yaml"))
    definitions = [load_yaml_file(f) for f in sorted(definition_files)]

    # Load data contract
    contract_file = project_root / "order-data-contract.yaml"
    contract = load_yaml_file(contract_file) if contract_file.exists() else None

    # Collect unique team/owner IDs from definitions and data contract
    owners = set()
    for definition in definitions:
        owner = definition.get("owner")
        if owner:
            owners.add(owner)

    # Also add domain from data contract as a team
    if contract:
        domain = contract.get("domain")
        if domain:
            owners.add(domain)

    # Create teams first
    print("Creating teams...")
    for owner in sorted(owners):
        create_team(api_key, base_url, owner)
    print()

    # Upload business definitions
    print("Uploading business definitions...")
    success_count = 0
    fail_count = 0

    for definition in definitions:
        if upload_definition(api_key, base_url, definition):
            success_count += 1
        else:
            fail_count += 1

    print(f"\nDefinitions: {success_count} uploaded, {fail_count} failed")
    print()

    # Upload data contract
    print("Uploading data contract...")

    if contract:
        # Transform file:// URLs to Entropy Data definition URLs
        org_slug = "apidays-semantics-demo-2025"
        transform_definition_urls(contract, base_url, org_slug)

        if upload_data_contract(api_key, base_url, contract):
            print("\nData contract uploaded successfully!")
        else:
            print("\nFailed to upload data contract")
            fail_count += 1
    else:
        print(f"  Warning: Data contract file not found: {contract_file}")

    print()
    print("Done!")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
