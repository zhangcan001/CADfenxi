from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
from ezdxf import recover


class DxfLoadError(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass
class DxfLoadResult:
    document: object
    warnings: list[str] = field(default_factory=list)


def load_dxf_document(file_path: str) -> DxfLoadResult:
    path = Path(file_path)
    if not path.exists():
        raise DxfLoadError("DXF_FILE_NOT_FOUND", "DXF 文件不存在。")
    try:
        return DxfLoadResult(document=ezdxf.readfile(path))
    except ezdxf.DXFStructureError:
        try:
            document, auditor = recover.readfile(path)
        except ezdxf.DXFVersionError as exc:
            raise DxfLoadError("DXF_UNSUPPORTED_VERSION", "DXF 版本不受支持。") from exc
        except (ezdxf.DXFError, OSError, ValueError) as exc:
            raise DxfLoadError("DXF_PARSE_FAILED", "DXF 解析失败。") from exc
        warnings = ["DXF_RECOVERED"] if getattr(auditor, "has_errors", False) else []
        return DxfLoadResult(document=document, warnings=warnings)
    except ezdxf.DXFVersionError as exc:
        raise DxfLoadError("DXF_UNSUPPORTED_VERSION", "DXF 版本不受支持。") from exc
    except OSError as exc:
        raise DxfLoadError("DXF_OPEN_FAILED", "DXF 文件无法打开。") from exc
    except (ezdxf.DXFError, ValueError) as exc:
        raise DxfLoadError("DXF_OPEN_FAILED", "DXF 文件无法打开。") from exc
