# IATA Order Data Model Demo

This project demonstrates a metadata-driven approach to API and data contract development using centralized business definitions.

## Project Structure

```
.
├── business-definitions/       # Centralized business field definitions
│   ├── flight/                 # Flight-related definitions
│   │   └── flight_number.yaml
│   ├── technical/              # Technical definitions
│   │   └── inserted_at.yaml
│   ├── order/                  # Order-related definitions
│   │   ├── line_item_no.yaml
│   │   ├── order_id.yaml
│   │   ├── order_status.yaml
│   │   ├── quantity.yaml
│   │   ├── total_amount.yaml
│   │   └── unit_price.yaml
│   └── passenger/              # Passenger-related definitions
│       ├── passenger_date_of_birth.yaml
│       └── passenger_name.yaml
├── order-api.yaml              # OpenAPI specification (minimal, references business definitions)
├── order-data-contract.yaml    # ODCS data contract (minimal, references business definitions)
├── postprocess.py              # Script to resolve references and generate documentation
└── gen/                        # Generated output (created by postprocess.py)
    ├── order-api-resolved.yaml
    ├── order-api.html
    ├── order-data-contract-resolved.yaml
    └── order-data-contract.html
```

## Business Definitions

Each business definition YAML file contains:

- `id`: Unique identifier
- `title`: Human-readable name (maps to `businessName` in ODCS)
- `owner`: Team responsible for the definition
- `type`: Logical data type
- `description`: Field description
- `classification`: Data classification (internal, confidential, sensitive)
- `pii`: Whether the field contains personally identifiable information
- `examples`: Example values
- `tags`: Categorization tags

## How It Works

1. **OpenAPI spec** (`order-api.yaml`) references business definitions via `x-business-definition`
2. **Data contract** (`order-data-contract.yaml`) references business definitions via `authoritativeDefinitions`
3. **Postprocessing** resolves references and copies metadata (description, type, examples, etc.)
4. **HTML documentation** is generated from the resolved files

## Usage

### Prerequisites

- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Node.js/npm (for Redocly CLI)

### Generate Documentation

```bash
uv run postprocess.py
```

This will:
1. Resolve business definitions in the OpenAPI spec → `gen/order-api-resolved.yaml`
2. Resolve business definitions in the data contract → `gen/order-data-contract-resolved.yaml`
3. Generate OpenAPI HTML documentation → `gen/order-api.html`
4. Generate data contract HTML documentation → `gen/order-data-contract.html`

### View Documentation

Open the generated HTML files in a browser:
- `gen/order-api.html` - API documentation (Redocly)
- `gen/order-data-contract.html` - Data contract documentation

## Key Features

- **Single source of truth**: Business definitions are defined once and reused
- **Separation of concerns**: Technical specs reference business metadata
- **Override support**: Properties in specs override business definitions
- **Automatic documentation**: HTML docs generated from resolved specs
- **ODCS v3.1.0**: Uses Open Data Contract Standard with relationships support
