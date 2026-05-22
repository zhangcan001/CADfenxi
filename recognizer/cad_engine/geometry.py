def point_to_list(value) -> list[float]:
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except Exception:
        return [0.0, 0.0, 0.0]


def dxf_get(entity, name: str, default=None):
    try:
        return entity.dxf.get(name, default)
    except Exception:
        return default


def entity_handle(entity) -> str | None:
    try:
        return entity.dxf.handle
    except Exception:
        return None
