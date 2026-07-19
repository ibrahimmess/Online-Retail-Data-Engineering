# Architecture and ETL Pipeline

## Objective

The pipeline converts the supplied Online Retail CSV into a reproducible PostgreSQL analytical warehouse.

## Data flow

```mermaid
flowchart LR
    A[CSV Source] --> B[Checksum and Archive]
    B --> C[Raw Text Layer]
    C --> D[Clean Staging Layer]
    D --> E[Dimensions and Fact]
    E --> F[Materialized Reporting Cache]
    C --> G[Audit Repository]
    D --> G
    E --> G