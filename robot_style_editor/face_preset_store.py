from pathlib import Path

from .config_face import (
    FACE_CONFIG_DIR,
    FACE_CONFIG_FILE,
    FACE_DEFAULT_HEADER,
)


def load_face_presets():
    presets = {}

    if not FACE_CONFIG_FILE.exists():
        return presets

    try:
        lines = FACE_CONFIG_FILE.read_text(encoding="utf-8").splitlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("[") and line.endswith("]"):
                name = line[1:-1].strip()

                header = FACE_DEFAULT_HEADER
                values = []

                if i + 1 < len(lines):
                    header_line = lines[i + 1].strip()
                    if header_line.startswith("<") and header_line.endswith(">"):
                        parts = [p.strip() for p in header_line[1:-1].split(",")]
                        if len(parts) == 3:
                            header = tuple(map(int, parts))

                j = i + 2
                value_text_parts = []
                while j < len(lines):
                    part = lines[j].strip()
                    if not part:
                        j += 1
                        continue

                    value_text_parts.append(part)
                    if "}" in part:
                        break
                    j += 1

                merged = " ".join(value_text_parts)
                merged = merged.replace("{", "").replace("}", "").replace(" ", "")
                if merged:
                    values = [int(x) for x in merged.split(",") if x != ""]

                if len(values) == 35:
                    presets[name] = {
                        "name": name,
                        "header": header,
                        "values": values,
                    }

                i = j

            i += 1

    except Exception as e:
        print(f"[face_preset_store] load error: {e}")

    return presets


def save_face_preset(name: str, header: tuple[int, int, int], values: list[int]):
    FACE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    presets = load_face_presets()
    if name in presets:
        raise ValueError(f"{name} はすでに存在します。")

    ms1, ms2, ms3 = header

    lines = []
    lines.append(f"[{name}]")
    lines.append(f"<{ms1}, {ms2}, {ms3}>")

    chunks = [
        values[:5],
        values[5:15],
        values[15:25],
        values[25:35],
    ]

    value_lines = []
    for i, chunk in enumerate(chunks):
        text = ",".join(map(str, chunk))
        if i == 0:
            value_lines.append("{ " + text + ",")
        elif i == len(chunks) - 1:
            value_lines.append(text + " }")
        else:
            value_lines.append(text + ",")

    lines.extend(value_lines)
    lines.append("")

    with open(FACE_CONFIG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))