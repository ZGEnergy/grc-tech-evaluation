# Data Researcher — Subagent Prompt Template

Research the following data availability question: **{{research_question}}**

## Context

### Scope Statement

{{scope_statement}}

### Target Repos

{{target_repos}}

### Table Hints

The orchestrator suggests these table name patterns may be relevant (use as starting points, not an exhaustive list):

{{relevant_tables_hint}}

## Instructions

Investigate what data is available in the internal Hive/Trino data warehouse to answer the research question. Use the data-mcp tools to perform exploratory data analysis. Produce a structured summary that directly answers the research question.

### Step 1 — Discover Relevant Tables

Use `mcp__data__list_tables` to list available tables. If a database name is apparent from the scope (e.g., `ercot`, `miso`, `caiso`), filter by that database. Otherwise, list all databases first to orient.

Search for tables matching the hint patterns. Also look for related tables that might be relevant but weren't hinted (e.g., if investigating price data, also check for load, weather, or generation tables that might be needed).

### Step 2 — Examine Table Schemas

For each relevant table found, use `mcp__data__describe_table` to get the full schema and semantic context. Pay attention to:
- Column names, types, and descriptions
- Partition columns (these indicate how data is organized and queried)
- Table descriptions and usage notes

### Step 3 — Sample Data

For the most relevant tables (limit to 3-5 tables), use `mcp__data__sample_data` to examine actual data. Look for:
- Data format and conventions (timestamps, timezone encoding, hour-ending vs hour-beginning)
- Value ranges and typical distributions
- NULL patterns or missing data indicators
- How categorical columns are encoded

### Step 4 — Check Data Freshness and Coverage

Use `mcp__data__query` to run targeted queries that establish:
- Date range coverage: `SELECT MIN(date_col), MAX(date_col) FROM table`
- Partition availability: check the most recent partitions
- Row counts or approximate sizes for capacity planning

Keep queries simple and read-only. Limit result sets to avoid large outputs.

### Step 5 — Check Existing Usage in Code (if applicable)

If the target repos are known, use Grep to search for table names, SQL queries, or data access patterns in the codebase. This reveals:
- How the data is currently consumed (SQL queries, Spark reads, pandas reads)
- Any transformations or filters applied at read time
- Schema assumptions encoded in the code (column name strings, Pandera schemas)

### Step 6 — Produce Structured Summary

Write a ~300 word summary with the sections below. Be specific: name actual tables, columns, and data characteristics. Avoid generic statements.

## Output Format

Produce a markdown report with the following sections:

## Available Tables

List the relevant tables found. For each, note:
- Fully qualified table name (`database.table`)
- Key columns relevant to the research question
- Partition scheme (if any)
- Approximate date range and freshness

## Schema Details

For the most important tables, describe:
- Column names and types that the plan will need to consume or produce
- Any conventions (hour-ending timestamps, timezone encoding, enum-like string columns)
- Relationships between tables (shared key columns, foreign-key-like patterns)

## Data Quality and Gaps

Note any concerns discovered during sampling:
- Missing data, NULL patterns, or known staleness issues
- Timezone or hour-convention ambiguities
- Partitions that may need explicit refresh (on-prem Hive tables from NAS)

## Existing Data Access Patterns

If code references were found, describe:
- How the data is currently read (SQL queries, Spark DataFrame reads, etc.)
- Filters, joins, or transformations applied at read time
- Any schema validation (Pandera schemas, column name constants)

## Key Findings

2-4 sentences directly answering `{{research_question}}`. State what data is available, what's missing, and any data-related constraints that the plan must account for.
