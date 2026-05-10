def get_speech_speed_multiplier(profile_source):
    if profile_source is None:
        return 1.0

    if hasattr(profile_source, "get_nested"):
        speed_data = profile_source.get_nested("speech_speed", {}) or {}
    elif isinstance(profile_source, dict):
        speed_data = profile_source.get("speech_speed", {}) or {}
    else:
        speed_data = {}

    try:
        return float(speed_data.get("value", 1.0) or 1.0)
    except (TypeError, ValueError):
        return 1.0


def apply_speech_speed_to_tts_instructions(instructions, profile_source):
    adjusted = dict(instructions or {})

    try:
        base_rate = float(adjusted.get("tts_rate", 1.0) or 1.0)
    except (TypeError, ValueError):
        base_rate = 1.0

    adjusted["tts_rate"] = round(
        base_rate * get_speech_speed_multiplier(profile_source),
        3,
    )
    return adjusted
