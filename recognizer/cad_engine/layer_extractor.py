def extract_layers(document) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    try:
        layers = document.layers
    except Exception:
        return names
    for layer in layers:
        try:
            name = str(layer.dxf.name)
        except Exception:
            continue
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names
