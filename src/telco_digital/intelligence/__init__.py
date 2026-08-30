"""Intelligence layer packages.

Facts stay in PostgreSQL. Predictions stay here. Do not write IS_CHURNING
into Neo4j. Every calculation must respect occurred_at <= as_of.
"""
