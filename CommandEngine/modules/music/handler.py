def run_play(slots: dict, entities: dict) -> dict:
    artist = slots.get("artist") or entities.get("artist")
    if artist:
        return {"text": f"Включаю {artist}."}
    return {"text": "Включаю музыку."}


def run_pause(slots: dict, entities: dict) -> dict:
    return {"text": "Музыка на паузе."}