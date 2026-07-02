def run(slots: dict, entities: dict) -> dict:
    city = slots.get("city") or entities.get("city") or "Москва"
    # здесь был бы реальный запрос к API погоды
    return {"text": f"В городе {city} сейчас +5°C, без осадков."}