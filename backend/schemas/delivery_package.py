from pydantic import BaseModel, Field


class DeliveryPackageRequest(BaseModel):
    include_original_files: bool = False
    include_cad_previews: bool = True
    include_pdf_previews: bool = True
    include_latest_excel: bool = True


class DeliveryPackageResult(BaseModel):
    package_id: str
    file_name: str
    file_size: int
    download_url: str
    included: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
