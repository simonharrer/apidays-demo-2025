#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
#     "datacontract-cli",
# ]
# ///
"""
Postprocess OpenAPI spec by resolving x-business-definition references
and copying properties from linked YAML files (unless already overridden).
"""

import yaml
from pathlib import Path


def load_yaml(path: Path) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict):
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def resolve_business_definition(ref: str, base_path: Path) -> dict | None:
    if not ref.startswith("file://"):
        return None
    file_path = base_path / ref.removeprefix("file://")
    if not file_path.exists():
        print(f"Warning: Business definition not found: {file_path}")
        return None
    return load_yaml(file_path)


def merge_properties(target: dict, source: dict):
    """Merge source properties into target, but only if not already present."""
    mapping = {
        'type': 'type',
        'description': 'description',
        'examples': 'examples',
        'enum': 'enum',
        'pattern': 'pattern',
        'classification': 'x-classification',
        'pii': 'x-pii',
        'criticalDataElement': 'x-criticalDataElement',
        'title': 'title',
    }

    for source_key, target_key in mapping.items():
        if source_key in source and target_key not in target:
            target[target_key] = source[source_key]


def process_schema(schema: dict, base_path: Path):
    """Recursively process schema and resolve business definitions."""
    if not isinstance(schema, dict):
        return

    if 'x-business-definition' in schema:
        ref = schema['x-business-definition']
        business_def = resolve_business_definition(ref, base_path)
        if business_def:
            merge_properties(schema, business_def)

    if 'properties' in schema:
        for prop in schema['properties'].values():
            process_schema(prop, base_path)

    if 'items' in schema:
        process_schema(schema['items'], base_path)

    if 'allOf' in schema:
        for item in schema['allOf']:
            process_schema(item, base_path)

    if 'oneOf' in schema:
        for item in schema['oneOf']:
            process_schema(item, base_path)

    if 'anyOf' in schema:
        for item in schema['anyOf']:
            process_schema(item, base_path)


def postprocess_openapi(input_path: Path, output_path: Path):
    """Postprocess OpenAPI spec."""
    base_path = input_path.parent

    spec = load_yaml(input_path)

    # Process component schemas
    if 'components' in spec and 'schemas' in spec['components']:
        for schema in spec['components']['schemas'].values():
            process_schema(schema, base_path)

    # Process path parameters
    if 'paths' in spec:
        for path in spec['paths'].values():
            for method in path.values():
                if isinstance(method, dict) and 'parameters' in method:
                    for param in method['parameters']:
                        if 'schema' in param:
                            process_schema(param['schema'], base_path)

    save_yaml(output_path, spec)
    print(f"Processed OpenAPI {input_path} -> {output_path}")


def process_odcs_property(prop: dict, base_path: Path):
    """Process ODCS property and resolve business definitions."""
    if 'authoritativeDefinitions' in prop:
        for auth_def in prop['authoritativeDefinitions']:
            if auth_def.get('type') == 'businessDefinition' and 'url' in auth_def:
                business_def = resolve_business_definition(auth_def['url'], base_path)
                if business_def:
                    # Map title -> businessName in ODCS
                    if 'title' in business_def and 'businessName' not in prop:
                        prop['businessName'] = business_def['title']
                    # Map type -> logicalType in ODCS
                    if 'type' in business_def and 'logicalType' not in prop:
                        prop['logicalType'] = business_def['type']
                    # Map description
                    if 'description' in business_def and 'description' not in prop:
                        prop['description'] = business_def['description']
                    # Map classification
                    if 'classification' in business_def and 'classification' not in prop:
                        prop['classification'] = business_def['classification']
                    # Map examples
                    if 'examples' in business_def and 'examples' not in prop:
                        prop['examples'] = business_def['examples']
                    # Map criticalDataElement
                    if 'criticalDataElement' in business_def and 'criticalDataElement' not in prop:
                        prop['criticalDataElement'] = business_def['criticalDataElement']


def postprocess_odcs(input_path: Path, output_path: Path):
    """Postprocess ODCS data contract."""
    base_path = input_path.parent

    contract = load_yaml(input_path)

    if 'schema' in contract:
        for obj in contract['schema']:
            if 'properties' in obj:
                for prop in obj['properties']:
                    process_odcs_property(prop, base_path)

    save_yaml(output_path, contract)
    print(f"Processed ODCS {input_path} -> {output_path}")


def generate_openapi_html(spec_path: Path, output_path: Path):
    """Generate HTML documentation from OpenAPI spec."""
    import subprocess
    subprocess.run([
        'npx', '@redocly/cli', 'build-docs', str(spec_path),
        '--output', str(output_path)
    ], check=True)
    print(f"Generated OpenAPI HTML: {output_path}")


def generate_datacontract_html(contract_path: Path, output_path: Path):
    """Generate HTML documentation from data contract."""
    import subprocess
    subprocess.run([
        'datacontract', 'export', str(contract_path),
        '--format', 'html',
        '--output', str(output_path)
    ], check=True)
    print(f"Generated Data Contract HTML: {output_path}")


if __name__ == '__main__':
    # Create gen folder
    gen_dir = Path('gen')
    gen_dir.mkdir(exist_ok=True)

    # Postprocess OpenAPI
    openapi_input = Path('order-api.yaml')
    openapi_output = gen_dir / 'order-api-resolved.yaml'
    postprocess_openapi(openapi_input, openapi_output)

    # Postprocess ODCS data contract
    odcs_input = Path('order-data-contract.yaml')
    odcs_output = gen_dir / 'order-data-contract-resolved.yaml'
    postprocess_odcs(odcs_input, odcs_output)

    # Generate HTML versions
    generate_openapi_html(openapi_output, gen_dir / 'order-api.html')
    generate_datacontract_html(odcs_output, gen_dir / 'order-data-contract.html')
