import asyncio

from app.framework.audit import (
    _LEDGER,
    _SITUATION_TYPES,
    record_decision,
    record_outcome,
    reset_audit_state,
    verify_chain,
)


def test_concurrent_record_decision_no_race():
    async def run_test():
        await reset_audit_state()

        async def one_call(idx: int):
            return await record_decision(
                alert_id=f"ALERT-CONC-{idx:03d}",
                situation_type="concurrency_test",
                action_taken="escalate",
                factors=[f"factor_{idx}"],
                confidence=0.8,
                kernel_type="unknown",
                noise_zone="unknown",
                conservation_status="unknown",
            )

        results = await asyncio.gather(*(one_call(idx) for idx in range(20)))
        chain_indices = [result["chain_index"] for result in results]

        assert len(chain_indices) == 20
        assert len(set(chain_indices)) == 20
        assert verify_chain()["verified"] is True

        await reset_audit_state()
        _SITUATION_TYPES.clear()

    asyncio.run(run_test())


def test_concurrent_record_outcome_no_corruption():
    async def run_test():
        await reset_audit_state()

        decisions = []
        for idx in range(8):
            decisions.append(
                await record_decision(
                    alert_id=f"ALERT-OUT-{idx:03d}",
                    situation_type="outcome_concurrency",
                    action_taken="escalate",
                    factors=[f"factor_{idx}"],
                    confidence=0.7,
                    kernel_type="unknown",
                    noise_zone="unknown",
                    conservation_status="unknown",
                )
            )

        outcomes = await asyncio.gather(
            *(
                record_outcome(
                    decision_id=decision["id"],
                    outcome="correct",
                    analyst_override=False,
                )
                for decision in decisions
            )
        )

        assert all(outcome is not None for outcome in outcomes)
        assert verify_chain()["verified"] is True

        decision_hashes = {decision["hash"] for decision in decisions}
        for entry in _LEDGER.entries():
            if getattr(entry, "decision_entry_hash", None) is not None:
                assert entry.decision_entry_hash in decision_hashes

        await reset_audit_state()
        _SITUATION_TYPES.clear()

    asyncio.run(run_test())


def test_interleaved_record_decision_and_outcome_concurrent():
    async def run_test():
        await reset_audit_state()

        # Seed 5 decisions sequentially so outcomes have valid targets.
        seed_decisions = []
        for idx in range(5):
            seed_decisions.append(
                await record_decision(
                    alert_id=f"ALERT-INTL-{idx:03d}",
                    situation_type="interleave_test",
                    action_taken="escalate",
                    factors=[f"factor_{idx}"],
                    confidence=0.8,
                    kernel_type="unknown",
                    noise_zone="unknown",
                    conservation_status="unknown",
                )
            )

        async def new_decision(idx):
            return await record_decision(
                alert_id=f"ALERT-INTL-NEW-{idx:03d}",
                situation_type="interleave_test",
                action_taken="monitor",
                factors=[f"new_factor_{idx}"],
                confidence=0.75,
                kernel_type="unknown",
                noise_zone="unknown",
                conservation_status="unknown",
            )

        async def new_outcome(decision):
            return await record_outcome(
                decision_id=decision["id"],
                outcome="correct",
                analyst_override=False,
            )

        # Submit 5 new decisions and 5 outcomes for seeded decisions concurrently.
        await asyncio.gather(
            *(new_decision(i) for i in range(5)),
            *(new_outcome(d) for d in seed_decisions),
        )

        assert verify_chain()["verified"] is True

        all_entries = list(_LEDGER.entries())
        chain_indices = [e.chain_index for e in all_entries]
        assert len(chain_indices) == len(set(chain_indices))

        await reset_audit_state()
        _SITUATION_TYPES.clear()

    asyncio.run(run_test())
