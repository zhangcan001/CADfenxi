import type {
  CadPipelineResponse,
  CadPipelineStep
} from "./api/cadPipeline";
import type { DrawingFile } from "./api/imports";
import type { FieldEvidence, FieldValue } from "./api/fusion";
import type { RecognitionCandidate } from "./api/candidates";
import type { BatchRecognitionResult, RecognitionRunResult } from "./api/recognition";

export function formatDate(value: string | null) {
  if (!value) {
    return "未打开";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function formatFileSize(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function isSupportedDrawingFile(name: string) {
  const lowerName = name.toLowerCase();
  return lowerName.endsWith(".pdf") || lowerName.endsWith(".dxf") || lowerName.endsWith(".dwg");
}

export function drawingFileLabel(name: string) {
  const lowerName = name.toLowerCase();
  if (lowerName.endsWith(".dxf")) {
    return "DXF";
  }
  if (lowerName.endsWith(".dwg")) {
    return "DWG";
  }
  return "PDF";
}

export function isCadReadyFile(file: DrawingFile) {
  return file.source_format === "dxf" || (file.source_format === "dwg" && file.convert_status === "success");
}

export function statusLabel(status: string) {
  const labels: Record<string, string> = {
    imported: "已导入",
    cad_pending: "待解析",
    cad_parsed: "已解析",
    preprocessed: "已预处理",
    recognized: "已生成推荐字段",
    need_review: "待校核",
    confirmed: "已确认",
    failed: "失败"
  };
  return labels[status] ?? status;
}

export function pipelineStepLabel(step: CadPipelineStep) {
  const labels: Record<CadPipelineStep, string> = {
    convert_dwg: "转换 DWG 为 DXF",
    prepare_dxf_sheet: "准备 DXF 图纸页",
    parse_dxf: "解析 DXF",
    generate_candidates: "生成候选值",
    fuse_fields: "生成推荐字段",
    generate_cad_preview: "生成 CAD 预览"
  };
  return labels[step];
}

export function pipelineStatusLabel(status: string) {
  const labels: Record<string, string> = {
    success: "成功",
    completed_with_errors: "完成但有错误",
    failed: "失败",
    skipped: "已跳过"
  };
  return labels[status] ?? status;
}

export function formatDuration(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 秒";
  }
  if (value < 60) {
    return `${value.toFixed(1)} 秒`;
  }
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes} 分 ${seconds} 秒`;
}

export function pipelineSuccessTotal(result: CadPipelineResponse) {
  return result.steps.reduce((total, step) => total + step.success_count, 0);
}

export function pipelineFailureTotal(result: CadPipelineResponse) {
  return result.steps.reduce((total, step) => total + step.failed_count, 0);
}

export function pipelineNextSuggestion(result: CadPipelineResponse) {
  if (result.errors.length > 0) {
    return "存在失败文件，请查看错误列表后重试。";
  }
  if (result.summary.fusion_success > 0) {
    return "已生成推荐字段，可以进入图纸台账查看结果。";
  }
  if (result.summary.candidate_success > 0) {
    return "候选值已生成，可以继续生成推荐字段。";
  }
  if (result.summary.parse_success > 0) {
    return "DXF 已解析，可以继续生成候选值。";
  }
  if (result.summary.converted_success > 0 || result.summary.sheet_prepared_success > 0) {
    return "CAD 文件已准备，可以继续解析 DXF。";
  }
  return "没有新的可处理对象，可以调整步骤或关闭跳过已完成步骤后重试。";
}

export function pipelineErrorSuggestion(errorCode: string) {
  const labels: Record<string, string> = {
    CONVERTER_NOT_CONFIGURED: "请先配置 DWG 转 DXF 工具。",
    DWG_CONVERT_FAILED: "请检查 DWG 文件是否损坏，或尝试用 CAD 软件手动转换。",
    DWG_CONVERT_TIMEOUT: "请减少单批数量，或检查转换工具是否卡住。",
    DWG_CONVERT_OUTPUT_MISSING: "请检查转换工具输出目录和 DXF 输出版本。",
    DXF_PARSE_FAILED: "请检查转换后的 DXF 是否有效。",
    CAD_PARSE_NOT_FOUND: "请先解析 DXF。",
    NO_CANDIDATES: "未生成候选值，请进入校核工作台人工补充。",
    DXF_CANDIDATE_EMPTY: "请检查 CAD JSON 中是否包含标题栏文字或块属性。",
    FIELD_FUSION_FAILED: "请检查候选值后重试，必要时人工补充字段。",
    CAD_PREVIEW_FILE_NOT_FOUND: "请检查 DXF 文件是否存在，或重新上传图纸。",
    CAD_PREVIEW_DXF_OPEN_FAILED: "请用 CAD 软件打开该 DXF，确认文件未损坏。",
    CAD_PREVIEW_TIMEOUT: "图纸较大或复杂，建议单独重新生成预览。",
    CAD_PREVIEW_RENDER_FAILED: "请尝试重新生成，或使用 CAD 软件查看。",
    CAD_PREVIEW_FILE_MISSING: "预览文件缺失，请重新生成 CAD 预览。",
    CAD_PREVIEW_FILE_MISSING_REGENERATED: "预览文件曾缺失，系统已尝试重新生成。"
  };
  return labels[errorCode] ?? "请查看文件状态并重试。";
}

export function cadPreviewStatusLabel(status: string | null, hasPreviewPath: boolean, errorCode?: string | null) {
  if (status === "success" && hasPreviewPath) {
    return "已生成";
  }
  if (status === "failed") {
    return errorCode === "CAD_PREVIEW_FILE_MISSING" ? "文件缺失" : "生成失败";
  }
  if (status === "skipped") {
    return "已跳过";
  }
  return "未生成";
}

export function dataHealthStatusLabel(status: string) {
  const labels: Record<string, string> = {
    ok: "正常",
    info: "提示",
    warning: "需关注",
    error: "异常"
  };
  return labels[status] ?? status;
}

export function dataHealthSuggestion(errorCode: string | null | undefined) {
  const labels: Record<string, string> = {
    APP_DATA_NOT_WRITABLE: "请检查目录权限或软件所在磁盘是否只读。",
    DATABASE_FILE_MISSING: "请确认 app_data/database/app.db 是否已复制或重新启动系统初始化。",
    PROJECT_DIR_MISSING: "请确认是否完整复制了 app_data/projects 目录。",
    DRAWING_FILE_MISSING: "请确认是否完整复制了 app_data/projects 目录。",
    CONVERTED_DXF_MISSING: "可重新执行 DWG 转 DXF。",
    SHEET_PREVIEW_MISSING: "可重新生成图纸页预览。",
    SHEET_THUMBNAIL_MISSING: "可重新生成图纸页缩略图。",
    TITLE_CROP_MISSING: "可重新生成标题栏裁剪图。",
    CAD_JSON_MISSING: "可重新执行 DXF 解析。",
    CAD_PREVIEW_MISSING: "可重新生成 CAD 预览。",
    EXPORT_FILE_MISSING: "可重新导出 Excel。",
    BACKUP_FILE_MISSING: "请确认备份 zip 是否被手动移动或删除。",
    ORPHAN_FILE_FOUND: "请人工确认后再手动处理，本版本不会自动删除项目文件。",
    FAILED_SHEET_EXISTS: "请查看失败图纸的 error_code 和 message 后重试对应步骤。",
    OPEN_ERROR_EXISTS: "建议在校核工作台处理后再交付或归档。",
    LOW_CONFIDENCE_EXISTS: "建议抽查低可信图纸。",
    UNREVIEWED_SHEETS_EXISTS: "这是校核进度提示，交付前建议完成确认。",
    TEMP_CLEANUP_FILES_FOUND: "可使用安全清理临时文件。",
    DATA_HEALTH_DRAWING_FILE_MISSING: "请确认是否完整复制了 app_data/projects 目录。",
    DATA_HEALTH_SHEET_PREVIEW_MISSING: "可重新生成图纸页预览。",
    DATA_HEALTH_CAD_JSON_MISSING: "可重新执行 DXF 解析。",
    DATA_HEALTH_CAD_PREVIEW_MISSING: "可重新生成 CAD 预览。",
    DATA_HEALTH_DWG_CONVERTED_FILE_MISSING: "可重新执行 DWG 转 DXF。",
    DATA_HEALTH_EXPORT_FILE_MISSING: "可重新导出 Excel。",
    DATA_HEALTH_BACKUP_FILE_MISSING: "请确认备份 zip 是否被手动移动或删除。",
    DATA_HEALTH_ORPHAN_FILES_FOUND: "请人工确认后再手动处理，本版本不会自动删除项目文件。",
    DATA_HEALTH_TEMP_FILES_FOUND: "可使用安全清理临时文件。",
    DATA_HEALTH_DIRECTORY_NOT_WRITABLE: "请检查目录权限或软件所在磁盘是否只读。"
  };
  return errorCode ? labels[errorCode] ?? "请查看检查项详情后处理。" : "无需处理。";
}

export function formatApiError(error: unknown, fallback: string) {
  const suggestionForCode = (errorCode: string) => {
    if (errorCode === "NETWORK_ERROR") {
      return "请确认后端服务已启动，并保持本地窗口不要关闭。";
    }
    if (errorCode === "REQUEST_TIMEOUT") {
      return "请稍后重试；如果正在处理大图纸，建议减少单批数量。";
    }
    if (errorCode.startsWith("CAD_PREVIEW")) {
      return pipelineErrorSuggestion(errorCode);
    }
    if (errorCode.includes("BACKUP")) {
      return "请检查 app_data/backups 是否可写，必要时重新创建备份。";
    }
    if (errorCode.includes("EXPORT")) {
      return "请确认当前项目有图纸，并检查导出目录是否可写。";
    }
    return errorCodeMessage(errorCode, "请根据错误说明处理后重试。");
  };

  if (error && typeof error === "object") {
    const maybe = error as { errorCode?: string | null; message?: string };
    if (maybe.errorCode) {
      const message =
        maybe.errorCode === "NETWORK_ERROR"
          ? "后端未连接或服务未启动。"
          : errorCodeMessage(maybe.errorCode, maybe.message || fallback);
      return [
        "操作失败",
        `错误码：${maybe.errorCode}`,
        `说明：${message}`,
        `建议：${suggestionForCode(maybe.errorCode)}`
      ].join("\n");
    }
    if (maybe.message) {
      return maybe.message;
    }
  }
  return fallback;
}

export function recommendedCandidate(fieldName: string, candidates: RecognitionCandidate[]) {
  return candidates
    .filter((candidate) => candidate.field_name === fieldName)
    .sort((left, right) => right.confidence - left.confidence || left.id - right.id)[0];
}

export function fieldSourceDescription(value: FieldValue | undefined, evidence: FieldEvidence[]) {
  if (!value) {
    return "暂无推荐字段";
  }
  const related = evidence.find((item) => item.field_value_id === value.id);
  if (related) {
    return `来自${sourceTypeLabel(related.source_type)}，原始文本：${related.raw_text || "-"}`;
  }
  if (value.final_source === "manual") {
    return "来自人工确认";
  }
  return `来自${sourceTypeLabel(value.final_source)}`;
}

export function errorCodeMessage(errorCode: string, fallback: string) {
  const labels: Record<string, string> = {
    DWG_NOT_SUPPORTED: "旧版本不支持 DWG；当前版本请先配置转换工具再转换为 DXF。",
    DWG_NOT_CONVERTED: "该 DWG 尚未转换为 DXF，请先执行 DWG 转 DXF。",
    CONVERTER_NOT_CONFIGURED: "未配置转换工具。",
    CONVERTER_NOT_FOUND: "未找到转换工具，请检查路径。",
    CONVERTER_NOT_EXECUTABLE: "转换工具不可执行，请检查权限。",
    CONVERTER_CHECK_FAILED: "转换工具检测失败。",
    DWG_CONVERT_FAILED: "DWG 转 DXF 失败，请检查转换工具输出。",
    DWG_CONVERT_OUTPUT_MISSING: "转换命令执行完成但未找到 DXF 输出文件。",
    DWG_CONVERT_TIMEOUT: "DWG 转 DXF 超时。",
    CAD_PARSE_NOT_FOUND: "未找到 CAD 解析结果，请先解析 DXF。",
    PROJECT_NOT_FOUND: "项目不存在。",
    IMPORT_SAVE_FAILED: "文件保存失败。",
    DUPLICATE_FILE: "文件疑似已导入过。",
    UNSUPPORTED_FILE_TYPE: "当前文件格式不支持。",
    FILE_TOO_LARGE: "文件超过大小限制。",
    EMPTY_FILE: "文件为空。",
    UNSUPPORTED_CAD_FORMAT: "当前操作仅支持 DXF 文件。",
    DXF_CANDIDATE_EMPTY: "DXF 候选值生成失败或为空。",
    NO_CANDIDATES: "未找到可用于融合的候选值。",
    FIELD_FUSION_FAILED: "推荐字段融合失败。",
    DXF_PARSE_FAILED: "DXF 解析失败，请检查文件是否损坏或版本是否受支持。",
    DXF_OPEN_FAILED: "DXF 文件无法打开，请检查文件是否损坏。",
    DXF_EMPTY_CONTENT: "DXF 可读取，但未提取到文字或块属性。"
  };
  return labels[errorCode] ?? fallback;
}

export function formatPoint(value: unknown) {
  return Array.isArray(value) ? `[${value.join(", ")}]` : "-";
}

export function sourceTypeLabel(sourceType: string) {
  const labels: Record<string, string> = {
    cad_text: "CAD 文字",
    cad_mtext: "CAD 多行文字",
    cad_block_attr: "CAD 块属性",
    cad_layer: "CAD 图层",
    cad_filename: "CAD 文件名",
    mixed: "多来源一致",
    manual: "人工确认",
    filename: "文件名",
    pdf_text: "PDF 文本",
    title_ocr: "标题栏 OCR",
    rule: "规则推断"
  };
  return labels[sourceType] ?? sourceType;
}

export function fieldNameLabel(fieldName: string) {
  const labels: Record<string, string> = {
    drawing_no: "图纸编号",
    drawing_name: "图纸名称",
    discipline: "专业",
    version: "版本",
    issue_date: "出图日期"
  };
  return labels[fieldName] ?? fieldName;
}

export function singleRecognitionAsBatch(
  item: RecognitionRunResult,
  batchId: number
): BatchRecognitionResult {
  return {
    batch_id: batchId,
    total_count: 1,
    success_count: item.status === "success" ? 1 : 0,
    failed_count: item.status === "failed" ? 1 : 0,
    items: [item]
  };
}
