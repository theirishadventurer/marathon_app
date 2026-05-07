from sqlalchemy import select


async def test_plan_history_table_exists_and_inserts(seeded_db):
    from app.models.plan import Plan
    from app.models.plan_history import PlanHistory

    plan = (await seeded_db.execute(select(Plan).limit(1))).scalar_one()
    row = PlanHistory(
        plan_id=plan.id,
        action="test_action",
        payload_json={"k": "v"},
    )
    seeded_db.add(row)
    await seeded_db.commit()

    result = await seeded_db.execute(select(PlanHistory).where(PlanHistory.plan_id == plan.id))
    persisted = result.scalar_one()
    assert persisted.action == "test_action"
    assert persisted.payload_json == {"k": "v"}
