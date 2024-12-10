"Script to find parent-child and broader-than relationships in the UMLS"

from collections import Counter
from datetime import datetime
from pathlib import Path
import argparse
import logging
import time

from tqdm import tqdm
import networkx as nx
import csv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("analysis.log")],
)
logger = logging.getLogger(__name__)


def parse_umls(file_path):
    """
    Parse the UMLS dataset in RFF format and extract relevant relationships.

    Args:
        file_path (str): Path to the UMLS RRF file

    Returns:
        tuple: Contains lists of edges and relationship information
    """
    parent_child_edges = set()
    broader_than_edges = set()
    relationship_types = set()
    duplicate_edges = Counter()
    self_loops = set()

    # First count total lines for the progress bar
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"UMLS file not found: {file_path}")

    total_lines = sum(1 for _ in open(file_path, "r", encoding="utf-8"))

    with open(file_path, "r", encoding="utf-8") as f:
        for line in tqdm(f, total=total_lines, desc="Parsing UMLS dataset"):
            if line.startswith("#") or not line.strip():
                continue

            try:
                parts = line.strip().split("|")
                if len(parts) < 5:
                    continue

                source = parts[0].strip()  # CUI1
                target = parts[4].strip()  # CUI2
                rel = parts[3].strip()  # REL

                relationship_types.add(rel)

                # Check for self-loops
                if source == target:
                    self_loops.add((source, rel))
                    continue

                # Create edge tuple and track duplicates
                if rel in ["CHD", "PAR", "RB", "RN"]:
                    edge = None
                    if rel == "CHD":  # Child
                        edge = (target, source)
                    elif rel == "PAR":  # Parent
                        edge = (source, target)
                    elif rel == "RB":  # Broader
                        edge = (source, target)
                    elif rel == "RN":  # Narrower
                        edge = (target, source)

                    if edge:
                        duplicate_edges[edge] += 1

                        # Add edges to appropriate sets
                        if rel in ["CHD", "PAR"]:
                            parent_child_edges.add(edge)
                        else:  # RB or RN
                            broader_than_edges.add(edge)

            except Exception as e:
                logger.error("Error processing line: %s", line.strip())
                logger.error("Error details: %s", str(e))
                continue

    return (
        list(parent_child_edges),
        list(broader_than_edges),
        relationship_types,
        dict(duplicate_edges),
        self_loops,
    )


def detect_cycles(graph):
    """
    Detect cycles in a directed graph with detailed path information using
    Depth First Search (DFS) algorithm.

    Args:
        graph (nx.DiGraph): Input directed graph

    Returns:
        tuple: (detailed_cycles, duration)
    """
    start_time = time.time()
    detailed_cycles = []
    visited = set()
    rec_stack = set()
    unique_cycles = set()

    # Sort nodes to ensure consistent traversal order
    sorted_nodes = sorted(graph.nodes())

    def dfs_cycle(node, path):
        """
        Depth First Search (DFS) to detect cycles in a directed graph.

        Args:
            node (graph node): Current node in the DFS traversal
            path (list): List of nodes visited in the current path

        Returns:
            None
        """
        if node in rec_stack:
            cycle_start = path.index(node)
            cycle = path[cycle_start:]

            normalized = normalize_cycle(cycle)
            if normalized not in unique_cycles and validate_cycle(
                graph,
                cycle,
            ):
                unique_cycles.add(normalized)
                cycle_info = {
                    "nodes": cycle,
                    "paths": [
                        [cycle[i], cycle[(i + 1) % len(cycle)]]
                        for i in range(len(cycle))
                    ],
                }
                detailed_cycles.append(cycle_info)
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Sort neighbors to ensure consistent order
        for neighbor in sorted(graph.neighbors(node)):
            dfs_cycle(neighbor, path)

        path.pop()
        rec_stack.remove(node)

    # Start DFS from each sorted node to find all cycles
    for node in tqdm(
        sorted_nodes,
        desc="Detecting cycles",
    ):
        if node not in visited:
            dfs_cycle(node, [])

    duration = time.time() - start_time
    return (
        detailed_cycles,
        duration,
    )


def detect_broader_than_violations(graph):
    """
    Detect broader-than rule violations with detailed path information.

    Args:
        graph (nx.DiGraph): Input directed graph

    Returns:
        tuple: (violations, duration)
    """
    start_time = time.time()
    violations = []

    # Calculate descendants for all nodes once to improve performance
    with tqdm(total=1, desc="Calculating descendants") as pbar:
        descendants_dict = {
            node: set(nx.descendants(graph, node)) for node in graph.nodes
        }
        pbar.update(1)

    # Add progress bar for nodes processing
    for source in tqdm(
        graph.nodes,
        desc="Checking broader-than violations",
    ):
        reachable = descendants_dict[source]
        for target in reachable:
            if source in descendants_dict[target]:
                try:
                    path_to_target = nx.shortest_path(
                        graph,
                        source,
                        target,
                    )
                    path_back_to_source = nx.shortest_path(
                        graph,
                        target,
                        source,
                    )
                    violations.append(
                        {
                            "source": source,
                            "target": target,
                            "circular_path": path_to_target + path_back_to_source[1:],
                        }
                    )
                except nx.NetworkXNoPath:
                    continue

    duration = time.time() - start_time
    return (
        violations,
        duration,
    )


def save_results_to_csv(
    parent_child_cycles,
    broader_than_violations,
    stats,
    duplicate_edges,
    self_loops,
    output_dir="./res/",
):
    """
    Save detection results to CSV files.

    Args:
        parent_child_cycles (list): List of detected cycles
        broader_than_violations (list): List of detected violations
        stats (dict): Analysis statistics
        duplicate_edges (dict): Dictionary of duplicate edges
        self_loops (set): Set of self-loop relationships
        output_dir (str): Output directory path

    Returns:
        tuple: Paths to created files
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_files = []

    with tqdm(total=5, desc="Saving results") as pbar:
        # Save parent-child cycles with detailed paths
        if parent_child_cycles:
            cycles_file = output_dir / f"parent_child_cycles_{timestamp}.csv"
            with open(
                cycles_file,
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Cycle_ID", "Cycle"])
                for i, cycle in enumerate(parent_child_cycles, 1):
                    nodes = " -> ".join(cycle["nodes"])
                    writer.writerow([i, nodes])
            results_files.append(cycles_file)
        else:
            results_files.append(None)
        pbar.update(1)

        # Save broader-than violations with circular paths
        if broader_than_violations:
            violations_file = output_dir / f"broader_than_violations_{timestamp}.csv"
            with open(
                violations_file,
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Violation_ID",
                        "Source",
                        "Target",
                        "Circular_Path",
                    ]
                )
                for i, violation in enumerate(broader_than_violations, 1):
                    circular_path = " -> ".join(violation["circular_path"])
                    writer.writerow(
                        [
                            i,
                            violation["source"],
                            violation["target"],
                            circular_path,
                        ]
                    )
            results_files.append(violations_file)
        else:
            results_files.append(None)
        pbar.update(1)

        # Save duplicate relationships
        duplicates_file = output_dir / f"duplicate_relationships_{timestamp}.csv"
        with open(
            duplicates_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["Source", "Target", "Count"])
            for (source, target), count in duplicate_edges.items():
                if count > 1:  # Only save actual duplicates
                    writer.writerow([source, target, count])
        results_files.append(duplicates_file)
        pbar.update(1)

        # Save self-loops
        self_loops_file = output_dir / f"self_loops_{timestamp}.csv"
        with open(
            self_loops_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["Concept", "Relationship_Type"])
            for concept, rel_type in self_loops:
                writer.writerow([concept, rel_type])
        results_files.append(self_loops_file)
        pbar.update(1)

        # Save statistics
        stats_file = output_dir / f"analysis_statistics_{timestamp}.csv"
        with open(
            stats_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            for key, value in stats.items():
                writer.writerow([key, value])
        results_files.append(stats_file)
        pbar.update(1)

    return tuple(results_files)


def normalize_cycle(cycle):
    """
    Convert a cycle to its canonical form for deduplication.

    The canonical form starts with the minimum value in the cycle and maintains
    the relative order of elements. This ensures that cycles with the same elements
    in different rotations are considered identical.

    Args:
        cycle (list): A list representing a cycle in the graph

    Returns:
        tuple: The normalized (canonical) form of the cycle
    """
    min_idx = cycle.index(min(cycle))
    return tuple(cycle[min_idx:] + cycle[:min_idx])


def validate_cycle(graph, cycle):
    """
    Verify that a cycle is valid by checking if all its edges exist in the graph.

    A valid cycle must have all consecutive nodes connected by edges in the graph,
    including the edge from the last node back to the first node.

    Args:
        graph (nx.DiGraph): The directed graph containing the edges
        cycle (list): A list of nodes representing a potential cycle

    Returns:
        bool: True if all edges in the cycle exist in the graph, False otherwise
    """
    for i in range(len(cycle)):
        source = cycle[i]
        target = cycle[(i + 1) % len(cycle)]
        if not graph.has_edge(source, target):
            return False
    return True


def analyze_parent_child_relations(file_path):
    """
    Analyze parent-child relationships and detect cycles.

    Args:
        file_path (str): Path to the UMLS RRF file

    Returns:
        tuple: (cycles, stats, results_files)
    """
    logger.info("Starting parent-child relationship analysis")

    with tqdm(total=4, desc="Parent-child analysis") as pbar:
        # Parse the dataset
        parent_child_edges, _, relationship_types, duplicate_edges, self_loops = (
            parse_umls(file_path)
        )
        pbar.update(1)

        # Build graph
        parent_child_graph = nx.DiGraph()
        parent_child_graph.add_edges_from(parent_child_edges)
        pbar.update(1)

        # Detect cycles
        parent_child_cycles, cycle_detection_time = detect_cycles(
            parent_child_graph,
        )
        pbar.update(1)

        # Collect statistics
        stats = {
            "Total_Parent_Child_Relationships": len(parent_child_edges),
            "Number_of_Parent_Child_Cycles": len(parent_child_cycles),
            "Total_Concepts": len(parent_child_graph.nodes),
            "Number_of_Self_Loops": len(self_loops),
            "Number_of_Duplicate_Relationships": sum(
                1 for count in duplicate_edges.values() if count > 1
            ),
            "Cycle_Detection_Time_Seconds": round(cycle_detection_time, 2),
        }
        # Add graph statistics to the stats dictionary
        pbar.update(1)

    # Save results
    results = save_results_to_csv(
        parent_child_cycles=parent_child_cycles,
        broader_than_violations=[],
        stats=stats,
        duplicate_edges=duplicate_edges,
        self_loops=self_loops,
        output_dir="./res/parent_child/",
    )

    return (
        parent_child_cycles,
        stats,
        results,
    )


def analyze_broader_than_relations(file_path):
    """
    Analyze broader-than relationships and detect violations.

    Args:
        file_path (str): Path to the UMLS RRF file

    Returns:
        tuple: (violations, stats, results_files)
    """
    logger.info("Starting broader-than relationship analysis")

    with tqdm(total=4, desc="Broader-than analysis") as pbar:
        # Parse the dataset
        _, broader_than_edges, relationship_types, duplicate_edges, self_loops = (
            parse_umls(file_path)
        )
        pbar.update(1)

        # Build graph
        broader_than_graph = nx.DiGraph()
        broader_than_graph.add_edges_from(broader_than_edges)
        pbar.update(1)

        # Detect violations
        broader_than_violations, violation_detection_time = (
            detect_broader_than_violations(broader_than_graph)
        )
        pbar.update(1)

        # Collect statistics
        stats = {
            "Total_Broader_Than_Relationships": len(broader_than_edges),
            "Number_of_Broader_Than_Violations": len(broader_than_violations),
            "Total_Concepts": len(broader_than_graph.nodes),
            "Number_of_Self_Loops": len(self_loops),
            "Number_of_Duplicate_Relationships": sum(
                1 for count in duplicate_edges.values() if count > 1
            ),
            "Violation_Detection_Time_Seconds": round(
                violation_detection_time,
                2,
            ),
        }
        pbar.update(1)

    # Save results
    results = save_results_to_csv(
        parent_child_cycles=[],
        broader_than_violations=broader_than_violations,
        stats=stats,
        duplicate_edges=duplicate_edges,
        self_loops=self_loops,
        output_dir="./res/broader_than/",
    )

    return (
        broader_than_violations,
        stats,
        results,
    )


def main():
    """Main execution function."""
    relationships = {
        "CHD": "Has child relationship",
        "PAR": "Has parent relationship",
        "RB": "Has a broader relationship",
        "RN": "Has a narrower relationship",
        "RO": "Has other relationship",
        "RQ": "Related and possibly synonymous",
        "SY": "Source asserted synonymy",
    }

    # Add argument parsing
    parser = argparse.ArgumentParser(description="Analyze UMLS relationships")
    parser.add_argument(
        "--type",
        "-t",
        choices=["parent-child", "broader-than", "both"],
        required=True,
        help="Type of analysis to perform",
    )
    parser.add_argument(
        "--input",
        "-i",
        default="./Dataset/MRREL.RRF",
        help="Path to input MRREL.RRF file",
    )
    args = parser.parse_args()

    try:
        if args.type in ["parent-child", "both"]:
            _cycles, pc_stats, _pc_results = analyze_parent_child_relations(args.input)
            logger.info("Parent-Child Analysis Results:")
            logger.info(
                "Found %d cycles",
                pc_stats["Number_of_Parent_Child_Cycles"],
            )
            logger.info(
                "Analysis took %s seconds",
                pc_stats["Cycle_Detection_Time_Seconds"],
            )

        if args.type in ["broader-than", "both"]:
            _violations, bt_stats, _bt_results = analyze_broader_than_relations(
                args.input
            )
            logger.info("Broader-Than Analysis Results:")
            logger.info(
                "Found %d violations",
                bt_stats["Number_of_Broader_Than_Violations"],
            )
            logger.info(
                "Analysis took %s seconds",
                bt_stats["Violation_Detection_Time_Seconds"],
            )

    except Exception as e:
        logger.error("Error during analysis: %s", str(e))
        raise


if __name__ == "__main__":
    main()
