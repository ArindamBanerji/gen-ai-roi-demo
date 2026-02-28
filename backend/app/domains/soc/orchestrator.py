"""
SOC factor orchestrator — async Neo4j → FactorComputer → GAE assembly.

Calls each FactorComputer in order, then delegates vector assembly to GAE.

Reference: docs/soc_copilot_design_v1.md §5.3.
"""

from gae.contracts import SchemaContract, PropertySpec
from gae.factors import assemble_factor_vector


async def compute_factor_vector(alert, computers, neo4j):
    """
    Async orchestrator.  Calls each FactorComputer, then delegates to GAE.

    Parameters
    ----------
    alert : dict | Alert
        Alert object with SOC context properties.
    computers : list[FactorComputer]
        Ordered list of FactorComputer instances (from config.get_factor_computers()).
    neo4j : Neo4jClient
        Async Neo4j client with run_query(query, params) method.

    Returns
    -------
    np.ndarray, shape (d_f,)
        Dense factor vector assembled by GAE assemble_factor_vector (Eq. 2).
    """
    values = []
    names = []
    for computer in computers:
        raw = await computer.compute(alert, neo4j)
        values.append(float(raw))
        names.append(computer.name)

    # Build raw dict + schema, then delegate to GAE
    raw_dict = {name: val for name, val in zip(names, values)}
    schema = SchemaContract(
        node_type="alert",
        properties=tuple(
            PropertySpec(name=n, required=False, default_value=0.5)
            for n in names
        ),
    )
    return assemble_factor_vector(raw_dict, schema)
