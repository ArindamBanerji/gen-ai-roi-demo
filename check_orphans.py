import psycopg
conn = psycopg.connect("host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres", autocommit=True)
cur = conn.cursor()
cur.execute("LOAD 'age'")
cur.execute("SET search_path = ag_catalog, public")
cur.execute("SELECT * FROM cypher('soc_graph', $$MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN d.action AS action, d.category AS category, count(d) AS cnt ORDER BY cnt DESC$$) AS (action agtype, category agtype, cnt agtype)")
print("Orphaned Decision nodes (no DECIDED_ON edge):")
for row in cur.fetchall():
    print(f"  action={row[0]}, category={row[1]}, count={row[2]}")
cur.execute("SELECT * FROM cypher('soc_graph', $$MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS total$$) AS (total agtype)")
print(f"Total orphaned: {cur.fetchone()[0]}")
conn.close()
