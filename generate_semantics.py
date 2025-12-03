#!/usr/bin/env python3
"""
Create an RDF model from business definitions YAML files and generate visualizations.
"""

import matplotlib.pyplot as plt
import networkx as nx
import yaml
from pathlib import Path
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, XSD, OWL, SKOS


# Define namespaces
BIZ = Namespace("http://example.org/business-definitions/")
SCHEMA = Namespace("http://schema.org/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCT = Namespace("http://purl.org/dc/terms/")


# =============================================================================
# RDF Model Creation
# =============================================================================

def load_business_definitions(base_path: str) -> list[dict]:
    """Load all business definition YAML files from the given path."""
    definitions = []
    base = Path(base_path)

    for yaml_file in base.rglob("*.yaml"):
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)
            if data and "id" in data:
                domain = yaml_file.parent.name
                data["domain"] = domain
                definitions.append(data)

    return definitions


def create_rdf_graph(definitions: list[dict]) -> Graph:
    """Create an RDF graph from business definitions."""
    g = Graph()

    # Bind namespaces
    g.bind("biz", BIZ)
    g.bind("schema", SCHEMA)
    g.bind("dcat", DCAT)
    g.bind("dct", DCT)
    g.bind("skos", SKOS)
    g.bind("owl", OWL)

    # Create domain classes
    domains = set(d["domain"] for d in definitions)
    for domain in domains:
        domain_uri = BIZ[f"Domain/{domain.title()}"]
        g.add((domain_uri, RDF.type, OWL.Class))
        g.add((domain_uri, RDFS.label, Literal(domain.title())))
        g.add((domain_uri, RDFS.subClassOf, BIZ["Domain"]))

    # Create the main Domain class
    g.add((BIZ["Domain"], RDF.type, OWL.Class))
    g.add((BIZ["Domain"], RDFS.label, Literal("Business Domain")))

    # Create BusinessDefinition class
    g.add((BIZ["BusinessDefinition"], RDF.type, OWL.Class))
    g.add((BIZ["BusinessDefinition"], RDFS.label, Literal("Business Definition")))

    # Create classification classes
    classifications = set(d.get("classification", "internal") for d in definitions)
    for classification in classifications:
        class_uri = BIZ[f"Classification/{classification.title()}"]
        g.add((class_uri, RDF.type, OWL.Class))
        g.add((class_uri, RDFS.label, Literal(classification.title())))

    # Create owner classes
    owners = set(d.get("owner", "unknown") for d in definitions)
    for owner in owners:
        owner_uri = BIZ[f"Owner/{owner}"]
        g.add((owner_uri, RDF.type, BIZ["Team"]))
        g.add((owner_uri, RDFS.label, Literal(owner)))

    g.add((BIZ["Team"], RDF.type, OWL.Class))
    g.add((BIZ["Team"], RDFS.label, Literal("Team")))

    # Process each business definition
    for defn in definitions:
        def_id = defn["id"].replace("/", "_")
        def_uri = BIZ[f"Definition/{def_id}"]

        g.add((def_uri, RDF.type, BIZ["BusinessDefinition"]))
        g.add((def_uri, RDFS.label, Literal(defn.get("title", def_id))))

        if "description" in defn:
            g.add((def_uri, RDFS.comment, Literal(defn["description"])))
            g.add((def_uri, DCT.description, Literal(defn["description"])))

        domain = defn.get("domain", "unknown")
        domain_uri = BIZ[f"Domain/{domain.title()}"]
        g.add((def_uri, BIZ["belongsToDomain"], domain_uri))

        owner = defn.get("owner", "unknown")
        owner_uri = BIZ[f"Owner/{owner}"]
        g.add((def_uri, BIZ["ownedBy"], owner_uri))

        if "type" in defn:
            g.add((def_uri, BIZ["dataType"], Literal(defn["type"])))

        if "format" in defn:
            g.add((def_uri, BIZ["format"], Literal(defn["format"])))

        if "pattern" in defn:
            g.add((def_uri, BIZ["pattern"], Literal(defn["pattern"])))

        classification = defn.get("classification", "internal")
        class_uri = BIZ[f"Classification/{classification.title()}"]
        g.add((def_uri, BIZ["hasClassification"], class_uri))

        if "pii" in defn:
            g.add((def_uri, BIZ["isPII"], Literal(defn["pii"], datatype=XSD.boolean)))

        if defn.get("criticalDataElement"):
            g.add((def_uri, BIZ["isCriticalDataElement"], Literal(True, datatype=XSD.boolean)))

        for tag in defn.get("tags", []):
            g.add((def_uri, DCAT.keyword, Literal(tag)))

        if "enum" in defn:
            for i, value in enumerate(defn["enum"]):
                enum_uri = BIZ[f"Definition/{def_id}/enum/{i}"]
                g.add((def_uri, BIZ["hasEnumValue"], enum_uri))
                g.add((enum_uri, RDF.type, BIZ["EnumValue"]))
                g.add((enum_uri, RDFS.label, Literal(value)))

        for example in defn.get("examples", []):
            g.add((def_uri, SKOS.example, Literal(str(example))))

    # Add property definitions
    properties = [
        (BIZ["belongsToDomain"], "Belongs to Domain", BIZ["BusinessDefinition"], BIZ["Domain"]),
        (BIZ["ownedBy"], "Owned by", BIZ["BusinessDefinition"], BIZ["Team"]),
        (BIZ["hasClassification"], "Has Classification", BIZ["BusinessDefinition"], None),
        (BIZ["hasEnumValue"], "Has Enum Value", BIZ["BusinessDefinition"], BIZ["EnumValue"]),
        (BIZ["dataType"], "Data Type", BIZ["BusinessDefinition"], None),
        (BIZ["isPII"], "Is PII", BIZ["BusinessDefinition"], None),
        (BIZ["isCriticalDataElement"], "Is Critical Data Element", BIZ["BusinessDefinition"], None),
    ]

    for prop_uri, label, domain_class, range_class in properties:
        if range_class:
            g.add((prop_uri, RDF.type, OWL.ObjectProperty))
            g.add((prop_uri, RDFS.range, range_class))
        else:
            g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        g.add((prop_uri, RDFS.label, Literal(label)))
        g.add((prop_uri, RDFS.domain, domain_class))

    # Add entity classes for Order, LineItem, Passenger, Flight
    g.add((BIZ["Order"], RDF.type, OWL.Class))
    g.add((BIZ["Order"], RDFS.label, Literal("Order")))
    g.add((BIZ["Order"], RDFS.comment, Literal("An order in the IATA NDC system")))

    g.add((BIZ["LineItem"], RDF.type, OWL.Class))
    g.add((BIZ["LineItem"], RDFS.label, Literal("Line Item")))
    g.add((BIZ["LineItem"], RDFS.comment, Literal("A line item within an order")))

    g.add((BIZ["Passenger"], RDF.type, OWL.Class))
    g.add((BIZ["Passenger"], RDFS.label, Literal("Passenger")))
    g.add((BIZ["Passenger"], RDFS.comment, Literal("A passenger associated with an order")))

    g.add((BIZ["Flight"], RDF.type, OWL.Class))
    g.add((BIZ["Flight"], RDFS.label, Literal("Flight")))
    g.add((BIZ["Flight"], RDFS.comment, Literal("A flight that can be booked")))

    # Add relationships between entities
    # Order hasPassenger Passenger
    g.add((BIZ["hasPassenger"], RDF.type, OWL.ObjectProperty))
    g.add((BIZ["hasPassenger"], RDFS.label, Literal("has Passenger")))
    g.add((BIZ["hasPassenger"], RDFS.comment, Literal("An order has one or more passengers")))
    g.add((BIZ["hasPassenger"], RDFS.domain, BIZ["Order"]))
    g.add((BIZ["hasPassenger"], RDFS.range, BIZ["Passenger"]))

    # Order hasLineItem LineItem
    g.add((BIZ["hasLineItem"], RDF.type, OWL.ObjectProperty))
    g.add((BIZ["hasLineItem"], RDFS.label, Literal("has Line Item")))
    g.add((BIZ["hasLineItem"], RDFS.comment, Literal("An order contains one or more line items")))
    g.add((BIZ["hasLineItem"], RDFS.domain, BIZ["Order"]))
    g.add((BIZ["hasLineItem"], RDFS.range, BIZ["LineItem"]))

    # LineItem isForFlight Flight
    g.add((BIZ["isForFlight"], RDF.type, OWL.ObjectProperty))
    g.add((BIZ["isForFlight"], RDFS.label, Literal("is for Flight")))
    g.add((BIZ["isForFlight"], RDFS.comment, Literal("A line item is for a specific flight")))
    g.add((BIZ["isForFlight"], RDFS.domain, BIZ["LineItem"]))
    g.add((BIZ["isForFlight"], RDFS.range, BIZ["Flight"]))

    # Link business definitions to their entity classes
    # Order domain definitions -> Order entity
    order_defs = ["order_order_id", "order_order_status", "order_total_amount"]
    for def_id in order_defs:
        def_uri = BIZ[f"Definition/{def_id}"]
        g.add((def_uri, BIZ["definesAttributeOf"], BIZ["Order"]))

    # Line item definitions -> LineItem entity
    line_item_defs = ["order_line_item_no", "order_quantity", "order_unit_price"]
    for def_id in line_item_defs:
        def_uri = BIZ[f"Definition/{def_id}"]
        g.add((def_uri, BIZ["definesAttributeOf"], BIZ["LineItem"]))

    # Passenger definitions -> Passenger entity
    passenger_defs = ["passenger_passenger_name", "passenger_passenger_date_of_birth"]
    for def_id in passenger_defs:
        def_uri = BIZ[f"Definition/{def_id}"]
        g.add((def_uri, BIZ["definesAttributeOf"], BIZ["Passenger"]))

    # Flight definitions -> Flight entity
    flight_defs = ["flight_flight_number"]
    for def_id in flight_defs:
        def_uri = BIZ[f"Definition/{def_id}"]
        g.add((def_uri, BIZ["definesAttributeOf"], BIZ["Flight"]))

    # Add definesAttributeOf property definition
    g.add((BIZ["definesAttributeOf"], RDF.type, OWL.ObjectProperty))
    g.add((BIZ["definesAttributeOf"], RDFS.label, Literal("defines attribute of")))
    g.add((BIZ["definesAttributeOf"], RDFS.comment, Literal("Links a business definition to the entity class it describes")))
    g.add((BIZ["definesAttributeOf"], RDFS.domain, BIZ["BusinessDefinition"]))

    return g


# =============================================================================
# Visualization Functions
# =============================================================================

def create_networkx_graph(rdf_graph: Graph) -> tuple[nx.DiGraph, dict]:
    """Create a NetworkX directed graph from an RDF graph."""
    G = nx.DiGraph()
    node_colors = {}

    for def_uri in rdf_graph.subjects(RDF.type, BIZ["BusinessDefinition"]):
        label = str(rdf_graph.value(def_uri, RDFS.label) or def_uri.split("/")[-1])
        G.add_node(label, node_type="definition")
        node_colors[label] = "#4CAF50"

        domain = rdf_graph.value(def_uri, BIZ["belongsToDomain"])
        if domain:
            domain_label = str(rdf_graph.value(domain, RDFS.label) or domain.split("/")[-1])
            G.add_node(domain_label, node_type="domain")
            node_colors[domain_label] = "#2196F3"
            G.add_edge(label, domain_label, relation="belongsToDomain")

        owner = rdf_graph.value(def_uri, BIZ["ownedBy"])
        if owner:
            owner_label = str(rdf_graph.value(owner, RDFS.label) or owner.split("/")[-1])
            G.add_node(owner_label, node_type="owner")
            node_colors[owner_label] = "#FF9800"
            G.add_edge(label, owner_label, relation="ownedBy")

        classification = rdf_graph.value(def_uri, BIZ["hasClassification"])
        if classification:
            class_label = str(rdf_graph.value(classification, RDFS.label) or classification.split("/")[-1])
            G.add_node(class_label, node_type="classification")
            node_colors[class_label] = "#9C27B0"
            G.add_edge(label, class_label, relation="hasClassification")

    return G, node_colors


def visualize_graph(G: nx.DiGraph, node_colors: dict, output_path: str):
    """Visualize the graph and save to file."""
    plt.figure(figsize=(16, 12))

    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    colors = [node_colors.get(node, "#gray") for node in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=2000, alpha=0.9)
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold")
    nx.draw_networkx_edges(G, pos, edge_color="#666666", arrows=True,
                           arrowsize=15, alpha=0.6, connectionstyle="arc3,rad=0.1")

    edge_labels = nx.get_edge_attributes(G, "relation")
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=6, alpha=0.8)

    legend_elements = [
        plt.scatter([], [], c="#4CAF50", s=200, label="Business Definition"),
        plt.scatter([], [], c="#2196F3", s=200, label="Domain"),
        plt.scatter([], [], c="#FF9800", s=200, label="Owner/Team"),
        plt.scatter([], [], c="#9C27B0", s=200, label="Classification"),
    ]
    plt.legend(handles=legend_elements, loc="upper left", fontsize=10)

    plt.title("Business Definitions RDF Model", fontsize=16, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Saved visualization to {output_path}")
    plt.close()


def create_domain_focused_view(rdf_graph: Graph, output_path: str):
    """Create a domain-focused hierarchical visualization."""
    plt.figure(figsize=(14, 10))

    G = nx.DiGraph()
    node_colors = {}

    G.add_node("Business\nDefinitions", node_type="root")
    node_colors["Business\nDefinitions"] = "#E91E63"

    domains = {}
    for def_uri in rdf_graph.subjects(RDF.type, BIZ["BusinessDefinition"]):
        label = str(rdf_graph.value(def_uri, RDFS.label) or def_uri.split("/")[-1])
        domain = rdf_graph.value(def_uri, BIZ["belongsToDomain"])
        if domain:
            domain_label = str(rdf_graph.value(domain, RDFS.label) or domain.split("/")[-1])
            if domain_label not in domains:
                domains[domain_label] = []
            domains[domain_label].append(label)

    for domain, definitions in domains.items():
        G.add_node(domain, node_type="domain")
        node_colors[domain] = "#2196F3"
        G.add_edge("Business\nDefinitions", domain)

        for defn in definitions:
            G.add_node(defn, node_type="definition")
            node_colors[defn] = "#4CAF50"
            G.add_edge(domain, defn)

    pos = nx.spring_layout(G, k=1.5, iterations=100, seed=42)

    domain_x_positions = {}
    domain_list = list(domains.keys())
    for i, domain in enumerate(domain_list):
        x = (i + 0.5) / len(domain_list)
        domain_x_positions[domain] = x
        pos[domain] = (x, 0.6)

    pos["Business\nDefinitions"] = (0.5, 1.0)

    for domain, definitions in domains.items():
        domain_x = domain_x_positions[domain]
        for i, defn in enumerate(definitions):
            offset = (i - (len(definitions) - 1) / 2) * 0.08
            pos[defn] = (domain_x + offset, 0.1 - i * 0.05)

    colors = [node_colors.get(node, "#gray") for node in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=2500, alpha=0.9)
    nx.draw_networkx_labels(G, pos, font_size=7, font_weight="bold")
    nx.draw_networkx_edges(G, pos, edge_color="#666666", arrows=True, arrowsize=12, alpha=0.5)

    legend_elements = [
        plt.scatter([], [], c="#E91E63", s=200, label="Root"),
        plt.scatter([], [], c="#2196F3", s=200, label="Domain"),
        plt.scatter([], [], c="#4CAF50", s=200, label="Business Definition"),
    ]
    plt.legend(handles=legend_elements, loc="upper right", fontsize=10)

    plt.title("Business Definitions by Domain", fontsize=16, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Saved domain view to {output_path}")
    plt.close()


def create_classification_matrix(rdf_graph: Graph, output_path: str):
    """Create a classification matrix visualization."""
    fig, ax = plt.subplots(figsize=(12, 8))

    data = []
    for def_uri in rdf_graph.subjects(RDF.type, BIZ["BusinessDefinition"]):
        label = str(rdf_graph.value(def_uri, RDFS.label) or "Unknown")
        domain = rdf_graph.value(def_uri, BIZ["belongsToDomain"])
        domain_label = str(rdf_graph.value(domain, RDFS.label) or "Unknown") if domain else "Unknown"
        classification = rdf_graph.value(def_uri, BIZ["hasClassification"])
        class_label = str(rdf_graph.value(classification, RDFS.label) or "Unknown") if classification else "Unknown"
        is_pii = rdf_graph.value(def_uri, BIZ["isPII"])
        pii_status = "Yes" if str(is_pii).lower() == "true" else "No"

        data.append({
            "name": label,
            "domain": domain_label,
            "classification": class_label,
            "pii": pii_status
        })

    data.sort(key=lambda x: (x["domain"], x["name"]))

    cell_text = [[d["name"], d["domain"], d["classification"], d["pii"]] for d in data]
    columns = ["Definition", "Domain", "Classification", "PII"]

    cell_colors = []
    class_color_map = {
        "Internal": "#E8F5E9",
        "Confidential": "#FFF3E0",
        "Sensitive": "#FFEBEE",
    }

    for row in data:
        base_color = class_color_map.get(row["classification"], "#FFFFFF")
        pii_color = "#FFCDD2" if row["pii"] == "Yes" else base_color
        cell_colors.append([base_color, "#E3F2FD", base_color, pii_color])

    table = ax.table(
        cellText=cell_text,
        colLabels=columns,
        cellColours=cell_colors,
        colColours=["#1976D2"] * 4,
        loc="center",
        cellLoc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.8)

    for j, col in enumerate(columns):
        cell = table[(0, j)]
        cell.set_text_props(color="white", fontweight="bold")

    ax.axis("off")
    ax.set_title("Business Definitions Classification Matrix", fontsize=14, fontweight="bold", pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Saved classification matrix to {output_path}")
    plt.close()


# =============================================================================
# Main
# =============================================================================

def main():
    script_dir = Path(__file__).parent
    definitions_path = script_dir / "business-definitions"
    gen_dir = script_dir / "gen-semantics"
    gen_dir.mkdir(exist_ok=True)

    # Load business definitions
    print("Loading business definitions...")
    definitions = load_business_definitions(definitions_path)
    print(f"Found {len(definitions)} business definitions")

    # Create RDF graph
    print("Creating RDF graph...")
    graph = create_rdf_graph(definitions)
    print(f"Created graph with {len(graph)} triples")

    # Serialize to different formats
    output_ttl = gen_dir / "business-definitions.ttl"
    output_rdf = gen_dir / "business-definitions.rdf"
    output_jsonld = gen_dir / "business-definitions.jsonld"

    graph.serialize(destination=output_ttl, format="turtle")
    print(f"Saved Turtle format to {output_ttl}")

    graph.serialize(destination=output_rdf, format="xml")
    print(f"Saved RDF/XML format to {output_rdf}")

    graph.serialize(destination=output_jsonld, format="json-ld")
    print(f"Saved JSON-LD format to {output_jsonld}")

    # Create visualizations
    print("\nCreating visualizations...")

    G, node_colors = create_networkx_graph(graph)
    visualize_graph(G, node_colors, gen_dir / "rdf-visualization.png")

    create_domain_focused_view(graph, gen_dir / "rdf-domain-view.png")
    create_classification_matrix(graph, gen_dir / "rdf-classification-matrix.png")

    print("\nDone! Generated files in the 'gen-semantics' directory.")


if __name__ == "__main__":
    main()
