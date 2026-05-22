from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.cad import (
    BatchCadParseResult,
    BatchDxfSheetPrepareResult,
    CadParseResult,
    CadParseSummary,
    DxfSheetPrepareResult,
)
from backend.schemas.cad_converter import (
    BatchDwgConvertResult,
    CadConversionRunRead,
    ConverterCheckResult,
    ConverterSettingCreate,
    ConverterSettingRead,
    ConverterSettingUpdate,
    DwgConvertResult,
)
from backend.services import cad_converter_service, cad_parse_service, cad_sheet_service

router = APIRouter(prefix="/api", tags=["cad"])


@router.get("/cad/converter-settings", response_model=list[ConverterSettingRead])
def list_converter_settings(db: Session = Depends(get_db)) -> list[ConverterSettingRead]:
    return cad_converter_service.list_converter_settings(db)


@router.post("/cad/converter-settings", response_model=ConverterSettingRead)
def create_converter_setting(
    payload: ConverterSettingCreate,
    db: Session = Depends(get_db),
) -> ConverterSettingRead:
    return cad_converter_service.create_converter_setting(db, payload)


@router.patch("/cad/converter-settings/{setting_id}", response_model=ConverterSettingRead)
def update_converter_setting(
    setting_id: int,
    payload: ConverterSettingUpdate,
    db: Session = Depends(get_db),
) -> ConverterSettingRead:
    return cad_converter_service.update_converter_setting(db, setting_id, payload)


@router.post("/cad/converter-settings/{setting_id}/check", response_model=ConverterCheckResult)
def check_converter_setting(
    setting_id: int,
    db: Session = Depends(get_db),
) -> ConverterCheckResult:
    return cad_converter_service.check_converter_setting(db, setting_id)


@router.post("/files/{file_id}/convert-dwg-to-dxf", response_model=DwgConvertResult)
def convert_dwg_file(file_id: int, db: Session = Depends(get_db)) -> DwgConvertResult:
    return cad_converter_service.convert_dwg_file(db, file_id)


@router.post("/imports/{batch_id}/convert-dwg-to-dxf", response_model=BatchDwgConvertResult)
def convert_dwg_batch(batch_id: int, db: Session = Depends(get_db)) -> BatchDwgConvertResult:
    return cad_converter_service.convert_dwg_batch(db, batch_id)


@router.get(
    "/projects/{project_id}/cad-conversion-runs",
    response_model=list[CadConversionRunRead],
)
def list_project_conversion_runs(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[CadConversionRunRead]:
    return cad_converter_service.list_project_conversion_runs(db, project_id)


@router.get("/files/{file_id}/cad-conversion-runs", response_model=list[CadConversionRunRead])
def list_file_conversion_runs(
    file_id: int,
    db: Session = Depends(get_db),
) -> list[CadConversionRunRead]:
    return cad_converter_service.list_file_conversion_runs(db, file_id)


@router.post("/files/{file_id}/prepare-dxf-sheet", response_model=DxfSheetPrepareResult)
def prepare_dxf_sheet(file_id: int, db: Session = Depends(get_db)) -> DxfSheetPrepareResult:
    return cad_sheet_service.prepare_dxf_sheet(db, file_id)


@router.post(
    "/imports/{batch_id}/prepare-dxf-sheets",
    response_model=BatchDxfSheetPrepareResult,
)
def prepare_dxf_sheets_for_batch(
    batch_id: int,
    db: Session = Depends(get_db),
) -> BatchDxfSheetPrepareResult:
    return cad_sheet_service.prepare_dxf_sheets_for_batch(db, batch_id)


@router.post("/files/{file_id}/parse-dxf", response_model=CadParseResult)
def parse_dxf_file(file_id: int, db: Session = Depends(get_db)) -> CadParseResult:
    return cad_parse_service.parse_dxf_file(db, file_id)


@router.post("/imports/{batch_id}/parse-dxf", response_model=BatchCadParseResult)
def parse_dxf_batch(batch_id: int, db: Session = Depends(get_db)) -> BatchCadParseResult:
    return cad_parse_service.parse_dxf_batch(db, batch_id)


@router.get("/sheets/{sheet_id}/cad-parse", response_model=CadParseSummary)
def get_cad_parse_summary(sheet_id: int, db: Session = Depends(get_db)) -> CadParseSummary:
    return cad_parse_service.get_cad_parse_summary(db, sheet_id)
