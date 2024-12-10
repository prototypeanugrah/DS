# UMLS (Unified Medical Language System) Relationship Analysis Tool

A Python tool for analyzing parent-child and broader-than relationships in UMLS datasets, detecting cycles, and identifying relationship violations.

## Features

- Parent-child relationship cycle detection
- Broader-than relationship violation detection
- Detailed analysis statistics
- CSV output generation for results
- Progress tracking with logging

## Dataset

### Source
The dataset used in this tool is the MRREL.RRF file from UMLS (Unified Medical Language System) 2024AA release, which can be obtained from:
- [UMLS 2024AA Dataset on Kaggle](https://www.kaggle.com/datasets/klilajaafer/umls-2024aa)

### MRREL.RRF File Description
MRREL.RRF (Relationship File) contains information about the relationships between concepts in the UMLS Metathesaurus. Each line in the file represents a relationship between two concepts.

#### File Format
The file is pipe-delimited (|) with the following columns:

| Column | Description |
|--------|-------------|
| CUI1 | Unique identifier of the first concept |
| AUI1 | Unique identifier for first atom |
| STYPE1 | The name of the column in MRCONSO.RRF that contains the identifier used for the first concept |
| REL | Relationship label |
| CUI2 | Unique identifier of the second concept |
| AUI2 | Unique identifier for second atom |
| STYPE2 | The name of the column in MRCONSO.RRF that contains the identifier used for the second concept |
| RELA | Additional relationship label |
| RUI | Unique identifier for relationship |
| SRUI | Source asserted relationship identifier |
| SAB | Abbreviated source name |
| SL | Source of relationship labels |
| RG | Relationship group |
| DIR | Source asserted directionality flag |
| SUPPRESS | Suppressible flag |
| CVF | Content View Flag |

#### Key Relationship Types
This tool specifically analyzes the following relationship types (found in the REL column):
- `PAR`: Parent relationship
- `CHD`: Child relationship
- `RB`: Broader relationship
- `RN`: Narrower relationship

#### Sample Record

C0000005|A0016458|AUI|RO|C0036775|A0016459|AUI|has_finding_site|R89178870||SNOMED_CT|SNOMED_CT|||Y|N||

In this example:
- C0000005 is related to C0036775
- The relationship type is 'RO' (has other relationship)
- The source is SNOMED_CT
- The specific relationship is 'has_finding_site'

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

```
res/
├── parent_child/
│   ├── parent_child_cycles_[timestamp].csv
│   ├── duplicate_relationships_[timestamp].csv
│   ├── self_loops_[timestamp].csv
│   └── analysis_stats_[timestamp].csv
└── broader_than/
    ├── broader_than_violations_[timestamp].csv
    ├── duplicate_relationships_[timestamp].csv
    ├── self_loops_[timestamp].csv
    └── analysis_stats_[timestamp].csv
```


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

## Understanding the Results

### Parent-Child Cycle Example
A parent-child cycle occurs when following parent-child relationships leads back to the original concept. 

Example cycle:

| Cycle_ID | Path |
|----------|------|
| Cycle 1  | C0205076 → C0441655 → C0205084 → C0205076 |

**What this means:**
- Concept C0205076 (Entire upper arm) is a parent of C0441655 (Structure of upper arm)
- C0441655 is a parent of C0205084 (Upper arm structure)
- C0205084 is a parent of C0205076 (Entire upper arm)

This creates an invalid circular hierarchy where a concept ends up being its own ancestor. In medical terminology, this is problematic because it creates logical inconsistencies in the classification system.

### Broader-Than Violation Example
A broader-than violation occurs when two concepts are defined as being broader than each other, either directly or through a chain of relationships.

Example violation:

| Violation_ID | Source | Target | Circular_Path |
|--------------|--------|--------|---------------|
| 1 | C0003962 | C0003963 | C0003962 → C0004096 → C0003963 → C0003962 |

**What this means:**
- C0003962 (Aspirin) is marked as broader than C0004096 (Salicylates)
- C0004096 is broader than C0003963 (Acetylsalicylic Acid)
- C0003963 is broader than C0003962 (Aspirin)

This creates an invalid semantic relationship where each concept is simultaneously broader and narrower than the others. In medical terminology, this violates the hierarchical nature of classification systems.

### Why These Issues Matter
- **Data Quality**: These inconsistencies can affect the quality of medical information systems
- **Clinical Decision Support**: Incorrect hierarchies can lead to problems in clinical decision support systems
- **Information Retrieval**: Search and retrieval systems may produce incorrect or incomplete results
- **Knowledge Organization**: These issues need to be resolved to maintain a logically consistent knowledge base
