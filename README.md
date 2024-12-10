# UMLS (Unified Medical Language System) Relationship Analysis Tool

A Python tool for analyzing parent-child and broader-than relationships in UMLS datasets, detecting cycles, and identifying relationship violations.

## Features

- Parent-child relationship cycle detection
- Broader-than relationship violation detection
- Detailed analysis statistics
- CSV output generation for results
- Progress tracking with logging

## Prerequisites

- Python 3.7+
- Required Python packages:
  ```
  networkx
  tqdm
  ```

## Installation

1. Clone this repository:
   ```
   git clone [repository-url]
   cd umls-relationship-analysis
   ```

2. Install required packages:
   ```
   pip install networkx tqdm
   ```

## Usage

The script can be run with the following command:
    ```
    python umls_relationship_analysis.py
    --type <analysis-type>
    --input <input-file-path>
    ```


### Arguments

- `--type` or `-t`: Type of analysis to perform
  - `parent-child`: Analyze parent-child relationships only
  - `broader-than`: Analyze broader-than relationships only
  - `both`: Perform both analyses
- `--input` or `-i`: Path to the input MRREL.RRF file (defaults to "./Dataset/MRREL.RRF")

### Input Data Format

The tool expects a UMLS MRREL.RRF file as input. This is a pipe-delimited (|) file with the following relevant columns:
- CUI1 (source concept)
- REL (relationship type)
- CUI2 (target concept)

Supported relationship types:
- CHD: Child relationship
- PAR: Parent relationship
- RB: Broader relationship
- RN: Narrower relationship

## Output

Results are saved in the following directory structure:
res/
├── parent_child/
│ ├── parent_child_cycles_[timestamp].csv
│ ├── duplicate_relationships_[timestamp].csv
│ ├── self_loops_[timestamp].csv
│ └── analysis_stats_[timestamp].csv
└── broader_than/
├── broader_than_violations_[timestamp].csv
├── duplicate_relationships_[timestamp].csv
├── self_loops_[timestamp].csv
└── analysis_stats_[timestamp].csv


### Output Files

1. **Parent-Child Cycles** (`parent_child_cycles_[timestamp].csv`):
   - Cycle_ID: Unique identifier for each cycle
   - Cycle: Sequence of concepts forming the cycle

2. **Broader-Than Violations** (`broader_than_violations_[timestamp].csv`):
   - Violation_ID: Unique identifier for each violation
   - Source: Source concept
   - Target: Target concept
   - Circular_Path: Complete path showing the violation

3. **Duplicate Relationships** (`duplicate_relationships_[timestamp].csv`):
   - Source: Source concept
   - Target: Target concept
   - Count: Number of times the relationship appears

4. **Self Loops** (`self_loops_[timestamp].csv`):
   - Concept: The concept ID
   - Relationship_Type: Type of self-referential relationship

5. **Analysis Stats** (`analysis_stats_[timestamp].csv`):
   - Various metrics including total relationships, processing time, and graph statistics
