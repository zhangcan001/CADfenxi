import logging

logger = logging.getLogger(__name__)


def point_to_list(value) -> list[float]:
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, IndexError, ValueError) as exc:
        logger.debug("point_to_list fallback for %r: %s", value, exc)
        return [0.0, 0.0, 0.0]


def dxf_get(entity, name: str, default=None):
    try:
        return entity.dxf.get(name, default)
    except AttributeError:
        return default


def entity_handle(entity) -> str | None:
    try:
        return entity.dxf.handle
    except AttributeError:
        return None
