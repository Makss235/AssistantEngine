def run(slots: dict, entities: dict) -> dict:
    city = slots.get("city") or entities.get("city") or "Москва"
    return {"text": f"В городе {city} сейчас +5°C, без осадков."}