# Recommendations

## Immediate improvements

1. Obtain business confirmation for the two negative-price bad-debt records.
2. Move archived datasets to durable object storage.
3. Use a managed orchestrator such as Airflow, Dagster, Prefect, or a cloud scheduler.
4. Establish data-quality owners and formal service-level thresholds.
5. Confirm whether future source files are snapshots or incremental deliveries.

## Scalability

- Process larger files in chunks.
- Create future partitions dynamically.
- Refresh reporting aggregates incrementally.
- Monitor unused indexes and database bloat.
- Consider BRIN indexes for very large time-based fact tables.

## Reliability

- Store credentials in a secret manager.
- Use least-privilege database roles.
- Add automated database backups and restore tests.
- Add CI integration tests with PostgreSQL.
- Use schema migrations such as Alembic or Flyway.

## Metadata

- Add OpenLineage-compatible events.
- Publish the data dictionary through a catalog.
- Track quality trends over multiple source versions.
- Record the Git commit with every pipeline run.

## Technology choices

Spark, Kafka, and Redis were intentionally excluded because the current dataset contains approximately 542,000 batch rows and has no streaming requirement. PostgreSQL, pandas, and a materialized view are sufficient at this scale.