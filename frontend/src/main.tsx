import React from "react";
import ReactDOM from "react-dom/client";
import {
  createProject,
  deleteProject,
  getProject,
  getProjectWorkbenchSummary,
  listProjects,
  updateProject,
  type Project,
  type ProjectWorkbenchSummary
} from "./api/projects";
import {
  listProjectFiles,
  uploadProjectPdfs,
  type DrawingFile,
  type ImportBatch
} from "./api/imports";
import {
  prepareDxfSheet,
  prepareDxfSheetsForBatch,
  parseDxfBatch,
  parseDxfFile,
  getCadParseSummary,
  type BatchCadParseResult,
  type BatchDxfSheetPrepareResult,
  type CadParseResult,
  type CadParseSummary,
  type DxfSheetPrepareResult
} from "./api/cad";
import {
  getCadPipelineJob,
  startCadPipeline,
  type BackgroundJobStatus,
  type CadPipelineRequest,
  type CadPipelineResponse,
  type CadPipelineStep
} from "./api/cadPipeline";
import {
  generateBatchCadPreview,
  generateCadPreview,
  generateProjectCadPreview,
  getCadPreviewImageUrl,
  type CadPreviewBatchPayload,
  type BatchCadPreviewResult,
  type CadPreviewResult
} from "./api/cadPreview";
import {
  checkConverterSetting,
  convertDwgBatch,
  convertDwgFile,
  getConverterSettings,
  listProjectConversionRuns,
  saveConverterSettings,
  type BatchDwgConvertResult,
  type CadConversionRun,
  type ConverterSetting,
  type DwgConvertResult
} from "./api/cadConverter";
import {
  getSheet,
  listProjectSheets,
  splitImportBatch,
  type BatchSplitResult,
  type DrawingSheet,
  type PaginatedSheets,
  type SheetQuery
} from "./api/sheets";
import {
  cropBatchTitles,
  cropSheetTitle,
  type BatchTitleCropResult,
  type TitleCropResult
} from "./api/titleCrops";
import {
  extractBatchText,
  extractSheetText,
  getOcrBatchJob,
  listRecognitionRuns,
  ocrBatchTitles,
  ocrSheetTitle,
  type BatchRecognitionResult,
  type OcrJobStatus,
  type RecognitionRun,
  type RecognitionRunResult
} from "./api/recognition";
import {
  generateBatchCandidates,
  generateSheetCandidates,
  listSheetCandidates,
  type BatchCandidateGenerateResult,
  type RecognitionCandidate
} from "./api/candidates";
import {
  fuseBatchFields,
  fuseSheetFields,
  listSheetEvidence,
  listSheetFieldValues,
  type BatchFusionResult,
  type DrawingIssue,
  type FieldEvidence,
  type FieldValue
} from "./api/fusion";
import { listProjectIssues, updateIssue, type PaginatedIssues } from "./api/issues";
import {
  adoptCandidate,
  batchConfirmProject,
  confirmSheet,
  getSheetAuditLogs,
  restoreRecommendedField,
  updateSheetFields,
  type AuditLog,
  type BatchConfirmResult
} from "./api/review";
import {
  createProjectBackup,
  deleteBackup,
  downloadBackupUrl,
  listProjectBackups,
  restoreBackupAsNewProject,
  verifyBackup,
  type BackupRecord,
  type BackupVerifyResult,
  type ProjectBackupResult,
  type RestoreBackupResult
} from "./api/backups";
import {
  checkExport,
  downloadExport,
  exportExcel,
  listExports,
  type ExportCheckResult,
  type ExportExcelResult,
  type ExportRecord
} from "./api/exports";
import {
  buildMaintenanceReport,
  cleanupTempFiles,
  getDataSafetySummary,
  runProjectHealthCheck,
  runSystemHealthCheck,
  scanProjectOrphanFiles,
  type DataHealthItem,
  type DataSafetySummary,
  type MaintenanceReportResult,
  type OrphanFileScanResult,
  type ProjectHealthResult,
  type SystemHealthResult,
  type TempCleanupResult
} from "./api/dataHealth";
import "./styles.css";
import type { HealthResponse } from "./types";
import { APP_VERSION } from "./constants";
import {
  drawingFileLabel,
  dataHealthStatusLabel,
  dataHealthSuggestion,
  errorCodeMessage,
  fieldNameLabel,
  fieldSourceDescription,
  cadPreviewStatusLabel,
  formatApiError,
  formatDate,
  formatDuration,
  formatFileSize,
  formatPoint,
  isCadReadyFile,
  isSupportedDrawingFile,
  pipelineErrorSuggestion,
  pipelineFailureTotal,
  pipelineNextSuggestion,
  pipelineStatusLabel,
  pipelineStepLabel,
  pipelineSuccessTotal,
  recommendedCandidate,
  singleRecognitionAsBatch,
  sourceTypeLabel,
  statusLabel
} from "./formatters";
import { AppHeader } from "./components/AppHeader";
import { CadPreviewViewer } from "./components/CadPreviewViewer";
import { CandidateGroups } from "./components/CandidateGroups";
import { EmbeddedTablesSection } from "./components/EmbeddedTablesSection";
import { FieldValueList } from "./components/FieldValueList";
import { Metric } from "./components/Metric";
import { ProjectsAside } from "./components/ProjectsAside";

function backupVerifyMessage(result: BackupVerifyResult) {
  if (result.errors.length > 0 || !result.valid) {
    return "备份包不完整，不建议恢复。";
  }
  if (result.warnings.length > 0) {
    return "备份包可恢复，但存在部分文件缺失或校验警告，恢复后请重点检查图纸预览和导出。";
  }
  return "备份包结构完整，可以用于恢复。";
}

function healthIssueItems(items: DataHealthItem[]) {
  return items.filter((item) => item.status !== "ok").slice(0, 8);
}

function groupLabel(group: string) {
  const labels: Record<string, string> = {
    storage: "存储",
    project_files: "项目文件",
    backup: "备份",
    export: "导出",
    restore: "恢复",
    temp: "临时文件"
  };
  return labels[group] ?? group;
}

function HealthGroupedSummary({ grouped }: { grouped: Record<string, { error: number; warning: number; info: number }> }) {
  const rows = Object.entries(grouped).filter(([, counts]) => counts.error + counts.warning + counts.info > 0);
  if (rows.length === 0) {
    return null;
  }
  return (
    <div className="health-group-grid">
      {rows.map(([group, counts]) => (
        <div className="health-group-card" key={group}>
          <strong>{groupLabel(group)}</strong>
          <span>异常 {counts.error}</span>
          <span>需关注 {counts.warning}</span>
          <span>提示 {counts.info}</span>
        </div>
      ))}
    </div>
  );
}

function HealthIssueList({ items }: { items: DataHealthItem[] }) {
  const issueItems = healthIssueItems(items);
  if (issueItems.length === 0) {
    return null;
  }
  return (
    <div className="file-list health-list">
      {issueItems.map((item, index) => (
        <div className={`file-row health-row ${item.status}`} key={`${item.scope}-${item.check_name}-${item.record_id ?? index}`}>
          <span>{dataHealthStatusLabel(item.status)}</span>
          <span>{groupLabel(item.scope)}</span>
          <span>{item.error_code || item.check_name}</span>
          <span title={item.path || undefined}>{item.path || item.scope}</span>
          <span>{item.message}</span>
          <span>{item.suggestion || dataHealthSuggestion(item.error_code)}</span>
        </div>
      ))}
    </div>
  );
}

type QuickAction = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  reason?: string;
  primary?: boolean;
  busy?: boolean;
  group?: "primary" | "review" | "output";
};

function QuickActionButton({ action }: { action: QuickAction }) {
  return (
    <div className={action.primary ? "quick-action primary" : "quick-action"}>
      <button
        type="button"
        onClick={action.onClick}
        disabled={action.disabled || action.busy}
        title={action.disabled || action.busy ? action.reason : undefined}
        aria-busy={action.busy ? "true" : undefined}
      >
        {action.busy ? `${action.label}中...` : action.label}
      </button>
      {(action.disabled || action.busy) && action.reason ? <span>{action.reason}</span> : null}
    </div>
  );
}

function ErrorNotice({ message }: { message: string }) {
  if (!message) {
    return null;
  }
  const lines = message.split("\n").filter(Boolean);
  return (
    <div className="error-notice" role="alert">
      <strong>{lines[0] ?? "操作失败"}</strong>
      {lines.slice(1).map((line) => (
        <span key={line}>{line}</span>
      ))}
    </div>
  );
}

function EmptyState({
  title,
  description,
  actionLabel,
  onAction
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="empty-state actionable-empty">
      <strong>{title}</strong>
      <span>{description}</span>
      {actionLabel && onAction ? (
        <button type="button" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

type TodoMetricTone = "normal" | "good" | "attention" | "warning" | "danger";

function TodoMetric({
  label,
  value,
  onClick,
  tone = "normal"
}: {
  label: string;
  value: number;
  onClick: () => void;
  tone?: TodoMetricTone;
}) {
  return (
    <button type="button" className={`todo-metric ${tone}`} onClick={onClick}>
      <span>{label}</span>
      <strong>{value}</strong>
    </button>
  );
}

const UPLOAD_MAX_BYTES = 200 * 1024 * 1024;

type DrawingFileKind = "pdf" | "dxf" | "dwg" | "unsupported";

type RejectedSelectedFile = {
  name: string;
  size: number;
  reason: string;
};

function drawingFileKind(name: string): DrawingFileKind {
  const lowerName = name.toLowerCase();
  if (lowerName.endsWith(".pdf")) {
    return "pdf";
  }
  if (lowerName.endsWith(".dxf")) {
    return "dxf";
  }
  if (lowerName.endsWith(".dwg")) {
    return "dwg";
  }
  return "unsupported";
}

function drawingKindLabel(kind: string) {
  const labels: Record<string, string> = {
    pdf: "PDF",
    dxf: "DXF",
    dwg: "DWG",
    unsupported: "不支持"
  };
  return labels[kind] ?? kind.toUpperCase();
}

function duplicateSelectedNames(files: File[]) {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  files.forEach((file) => {
    const key = file.name.trim().toLowerCase();
    if (seen.has(key)) {
      duplicates.add(file.name);
    }
    seen.add(key);
  });
  return Array.from(duplicates);
}

function existingProjectFileMatches(files: File[], projectFiles: DrawingFile[]) {
  const existingNames = new Set(projectFiles.map((file) => file.original_name.trim().toLowerCase()));
  return files
    .filter((file) => existingNames.has(file.name.trim().toLowerCase()))
    .map((file) => file.name);
}

function importItemStatusLabel(status: string) {
  const labels: Record<string, string> = {
    imported: "已导入",
    duplicate: "重复文件",
    unsupported: "不支持格式",
    failed: "导入失败"
  };
  return labels[status] ?? statusLabel(status);
}

function importNextSuggestion(result: ImportBatch, hasActiveConverter: boolean) {
  const hasPdf = result.files.some((file) => file.source_format === "pdf");
  const hasDxf = result.files.some((file) => file.source_format === "dxf");
  const hasDwg = result.files.some((file) => file.source_format === "dwg");
  if (!hasPdf && !hasDxf && !hasDwg) {
    return "本次没有可继续处理的新图纸，可以返回项目首页。";
  }
  if (hasPdf && hasDxf && hasDwg) {
    return "已导入多种图纸文件。建议按顺序处理：PDF 拆页 → DWG 转 DXF → CAD pipeline → 校核 → 导出 Excel。";
  }
  if (hasPdf && hasDxf) {
    return "已导入 PDF 和 DXF 图纸。建议先处理 PDF 拆页，再执行 CAD pipeline 处理 DXF。";
  }
  if (hasDxf && hasDwg) {
    return "已导入 DXF 和 DWG 图纸。建议先处理 DWG 转 DXF，再执行 CAD pipeline。";
  }
  if (hasPdf && hasDwg) {
    return "已导入 PDF 和 DWG 图纸。建议先生成 PDF 图纸页，再处理 DWG 转 DXF。";
  }
  if (hasPdf) {
    return "已导入 PDF 图纸。下一步建议生成图纸页预览。";
  }
  if (hasDxf) {
    return "已导入 DXF 图纸。下一步建议执行 CAD pipeline，完成解析、候选值生成和字段融合。";
  }
  if (hasDwg && !hasActiveConverter) {
    return "已导入 DWG 文件。系统不直接解析 DWG，请先配置外部 DWG 转 DXF 工具。";
  }
  return "已导入 DWG 文件。下一步建议执行 DWG 转 DXF，然后进入 DXF 识别流程。";
}

function App() {
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = React.useState(false);
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = React.useState<Project | null>(null);
  const [workbenchSummary, setWorkbenchSummary] = React.useState<ProjectWorkbenchSummary | null>(null);
  const [loadingProjects, setLoadingProjects] = React.useState(true);
  const [projectError, setProjectError] = React.useState("");
  const [formError, setFormError] = React.useState("");
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [editing, setEditing] = React.useState(false);
  const [editName, setEditName] = React.useState("");
  const [editDescription, setEditDescription] = React.useState("");
  const [importOpen, setImportOpen] = React.useState(false);
  const [selectedFiles, setSelectedFiles] = React.useState<File[]>([]);
  const [selectedRejectedFiles, setSelectedRejectedFiles] = React.useState<RejectedSelectedFile[]>([]);
  const [batchName, setBatchName] = React.useState("");
  const [remark, setRemark] = React.useState("");
  const [importError, setImportError] = React.useState("");
  const [importResult, setImportResult] = React.useState<ImportBatch | null>(null);
  const [projectFiles, setProjectFiles] = React.useState<DrawingFile[]>([]);
  const [sheets, setSheets] = React.useState<DrawingSheet[]>([]);
  const [selectedSheetIds, setSelectedSheetIds] = React.useState<number[]>([]);
  const [sheetPage, setSheetPage] = React.useState<PaginatedSheets>({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0
  });
  const [sheetQuery, setSheetQuery] = React.useState<SheetQuery>({
    page: 1,
    page_size: 20,
    sort_by: "default",
    sort_order: "asc"
  });
  const [splitResult, setSplitResult] = React.useState<BatchSplitResult | null>(null);
  const [splitError, setSplitError] = React.useState("");
  const [dxfPrepareResult, setDxfPrepareResult] =
    React.useState<DxfSheetPrepareResult | null>(null);
  const [batchDxfPrepareResult, setBatchDxfPrepareResult] =
    React.useState<BatchDxfSheetPrepareResult | null>(null);
  const [dxfPrepareError, setDxfPrepareError] = React.useState("");
  const [cadParseResult, setCadParseResult] = React.useState<CadParseResult | null>(null);
  const [batchCadParseResult, setBatchCadParseResult] =
    React.useState<BatchCadParseResult | null>(null);
  const [cadParseSummary, setCadParseSummary] = React.useState<CadParseSummary | null>(null);
  const [cadParseError, setCadParseError] = React.useState("");
  const [cadPreviewResult, setCadPreviewResult] = React.useState<CadPreviewResult | null>(null);
  const [batchCadPreviewResult, setBatchCadPreviewResult] = React.useState<BatchCadPreviewResult | null>(null);
  const [cadPreviewError, setCadPreviewError] = React.useState("");
  const [cadPreviewSkipCompleted, setCadPreviewSkipCompleted] = React.useState(true);
  const [cadPreviewForce, setCadPreviewForce] = React.useState(false);
  const [cadPreviewContinueOnError, setCadPreviewContinueOnError] = React.useState(true);
  const [busyAction, setBusyAction] = React.useState("");
  const [previewSheet, setPreviewSheet] = React.useState<DrawingSheet | null>(null);
  const [titleCropResult, setTitleCropResult] = React.useState<BatchTitleCropResult | null>(null);
  const [titleCropError, setTitleCropError] = React.useState("");
  const [recognitionResult, setRecognitionResult] =
    React.useState<BatchRecognitionResult | null>(null);
  const [recognitionError, setRecognitionError] = React.useState("");
  const [ocrJob, setOcrJob] = React.useState<OcrJobStatus | null>(null);
  const ocrJobPollRef = React.useRef<number | null>(null);
  const [recognitionRuns, setRecognitionRuns] = React.useState<RecognitionRun[]>([]);
  const [runsSheetId, setRunsSheetId] = React.useState<number | null>(null);
  const [candidateResult, setCandidateResult] =
    React.useState<BatchCandidateGenerateResult | null>(null);
  const [candidateError, setCandidateError] = React.useState("");
  const [candidates, setCandidates] = React.useState<RecognitionCandidate[]>([]);
  const [candidatesSheetId, setCandidatesSheetId] = React.useState<number | null>(null);
  const [fusionResult, setFusionResult] = React.useState<BatchFusionResult | null>(null);
  const [fusionError, setFusionError] = React.useState("");
  const [fieldValues, setFieldValues] = React.useState<FieldValue[]>([]);
  const [fieldEvidence, setFieldEvidence] = React.useState<FieldEvidence[]>([]);
  const [fieldValuesSheetId, setFieldValuesSheetId] = React.useState<number | null>(null);
  const [issues, setIssues] = React.useState<DrawingIssue[]>([]);
  const [issuePage, setIssuePage] = React.useState<PaginatedIssues>({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0
  });
  const [detailSheet, setDetailSheet] = React.useState<DrawingSheet | null>(null);
  const [reviewSheet, setReviewSheet] = React.useState<DrawingSheet | null>(null);
  const [reviewFields, setReviewFields] = React.useState<Record<string, string>>({});
  const [reviewNote, setReviewNote] = React.useState("");
  const [reviewError, setReviewError] = React.useState("");
  const [reviewMessage, setReviewMessage] = React.useState("");
  const [reviewSaveState, setReviewSaveState] = React.useState("");
  const [auditLogs, setAuditLogs] = React.useState<AuditLog[]>([]);
  const [batchConfirmResult, setBatchConfirmResult] = React.useState<BatchConfirmResult | null>(null);
  const [exportCheck, setExportCheck] = React.useState<ExportCheckResult | null>(null);
  const [exportResult, setExportResult] = React.useState<ExportExcelResult | null>(null);
  const [exportRecords, setExportRecords] = React.useState<ExportRecord[]>([]);
  const [exportError, setExportError] = React.useState("");
  const [backupResult, setBackupResult] = React.useState<ProjectBackupResult | null>(null);
  const [backupRecords, setBackupRecords] = React.useState<BackupRecord[]>([]);
  const [backupError, setBackupError] = React.useState("");
  const [backupBusy, setBackupBusy] = React.useState(false);
  const [restoreBusyId, setRestoreBusyId] = React.useState<number | null>(null);
  const [restoreResult, setRestoreResult] = React.useState<RestoreBackupResult | null>(null);
  const [deleteBackupBusyId, setDeleteBackupBusyId] = React.useState<number | null>(null);
  const [verifyBusyId, setVerifyBusyId] = React.useState<number | null>(null);
  const [verifyResults, setVerifyResults] = React.useState<Record<number, BackupVerifyResult>>({});
  const [converterSettings, setConverterSettings] = React.useState<ConverterSetting[]>([]);
  const [converterName, setConverterName] = React.useState("ODA File Converter");
  const [converterExePath, setConverterExePath] = React.useState("");
  const [converterOutputVersion, setConverterOutputVersion] = React.useState("ACAD2018");
  const [converterMessage, setConverterMessage] = React.useState("");
  const [converterError, setConverterError] = React.useState("");
  const [dwgConvertResult, setDwgConvertResult] = React.useState<DwgConvertResult | null>(null);
  const [batchDwgConvertResult, setBatchDwgConvertResult] =
    React.useState<BatchDwgConvertResult | null>(null);
  const [conversionRuns, setConversionRuns] = React.useState<CadConversionRun[]>([]);
  const [cadPipelineSteps, setCadPipelineSteps] = React.useState<CadPipelineStep[]>([
    "convert_dwg",
    "prepare_dxf_sheet",
    "parse_dxf",
    "generate_candidates",
    "fuse_fields"
  ]);
  const [cadPipelineSkipCompleted, setCadPipelineSkipCompleted] = React.useState(true);
  const [cadPipelineContinueOnError, setCadPipelineContinueOnError] = React.useState(true);
  const [cadPipelineResult, setCadPipelineResult] =
    React.useState<CadPipelineResponse | null>(null);
  const [cadPipelineError, setCadPipelineError] = React.useState("");
  const [cadPipelineStartedAt, setCadPipelineStartedAt] = React.useState<number | null>(null);
  const [cadPipelineElapsed, setCadPipelineElapsed] = React.useState(0);
  const [cadPipelineJob, setCadPipelineJob] = React.useState<BackgroundJobStatus | null>(null);
  const cadPipelineJobPollRef = React.useRef<number | null>(null);
  const cadPipelineProjectIdRef = React.useRef<number | null>(null);
  const [dataSafetySummary, setDataSafetySummary] = React.useState<DataSafetySummary | null>(null);
  const [systemHealthResult, setSystemHealthResult] = React.useState<SystemHealthResult | null>(null);
  const [projectHealthResult, setProjectHealthResult] = React.useState<ProjectHealthResult | null>(null);
  const [orphanScanResult, setOrphanScanResult] = React.useState<OrphanFileScanResult | null>(null);
  const [tempCleanupResult, setTempCleanupResult] = React.useState<TempCleanupResult | null>(null);
  const [maintenanceReportResult, setMaintenanceReportResult] =
    React.useState<MaintenanceReportResult | null>(null);
  const [maintenanceError, setMaintenanceError] = React.useState("");
  const [maintenanceBusy, setMaintenanceBusy] = React.useState("");

  React.useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Health check failed");
        }
        return response.json() as Promise<HealthResponse>;
      })
      .then((data) => {
        setHealth(data);
        setHealthError(false);
      })
      .catch(() => {
        setHealth(null);
        setHealthError(true);
      });
  }, []);

  const refreshProjects = React.useCallback(() => {
    setLoadingProjects(true);
    listProjects()
      .then((data) => {
        setProjects(data);
        setProjectError("");
      })
      .catch(() => {
        setProjectError("项目列表加载失败，请确认本地服务是否启动");
      })
      .finally(() => setLoadingProjects(false));
  }, []);

  React.useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  React.useEffect(() => {
    getDataSafetySummary()
      .then(setDataSafetySummary)
      .catch(() => setDataSafetySummary(null));
  }, []);

  React.useEffect(() => {
    if (cadPipelineStartedAt === null) {
      return;
    }
    const timer = window.setInterval(() => {
      setCadPipelineElapsed((Date.now() - cadPipelineStartedAt) / 1000);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cadPipelineStartedAt]);

  const handleCreateProject = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedDescription = description.trim();
    if (!trimmedName) {
      setFormError("项目名称不能为空");
      return;
    }

    createProject({
      name: trimmedName,
      description: trimmedDescription || undefined
    })
      .then((project) => {
        setProjects((current) => [project, ...current]);
        setSelectedProject(project);
        setWorkbenchSummary({
          project_id: project.id,
          drawing_file_count: 0,
          drawing_sheet_count: 0,
          unreviewed_count: 0,
          low_confidence_count: 0,
          missing_drawing_no_count: 0,
          missing_drawing_name_count: 0,
          open_error_count: 0,
          open_warning_count: 0,
          cad_preview_missing_count: 0,
          last_import_at: null,
          last_export_at: null,
          last_backup_at: null
        });
        setProjectFiles([]);
        setSheets([]);
        setSheetPage({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
        setBackupRecords([]);
        setBackupResult(null);
        setBackupError("");
        setRestoreResult(null);
        setVerifyResults({});
        setProjectHealthResult(null);
        setOrphanScanResult(null);
        setImportResult(null);
        setSelectedFiles([]);
        setSelectedRejectedFiles([]);
        setName("");
        setDescription("");
        setFormError("");
        setEditing(false);
      })
      .catch(() => setFormError("项目创建失败，请稍后重试"));
  };

  const handleOpenProject = (projectId: number) => {
    getProject(projectId)
      .then((project) => {
        setSelectedProject(project);
        loadWorkbenchSummary(project.id);
        setEditing(false);
        setEditName(project.name);
        setEditDescription(project.description ?? "");
        loadProjectFiles(project.id);
        loadProjectSheets(project.id);
        loadProjectBackups(project.id);
        getDataSafetySummary().then(setDataSafetySummary).catch(() => setDataSafetySummary(null));
        loadConverterSettings();
        loadConversionRuns(project.id);
        refreshProjects();
      })
      .catch(() => setProjectError("项目打开失败"));
  };

  const loadProjectFiles = (projectId: number) => {
    listProjectFiles(projectId)
      .then((files) => setProjectFiles(files))
      .catch(() => setProjectFiles([]));
  };

  const loadProjectSheets = (projectId: number, query: SheetQuery = sheetQuery) => {
    listProjectSheets(projectId, query)
      .then((data) => {
        setSheetPage(data);
        setSheets(data.items);
        setSelectedSheetIds((current) =>
          current.filter((id) => data.items.some((sheet) => sheet.id === id))
        );
      })
      .catch(() => setSheets([]));
    listProjectIssues(projectId, { page: 1, page_size: 20, status: "open" })
      .then((data) => {
        setIssuePage(data);
        setIssues(data.items);
      })
      .catch(() => setIssues([]));
    listExports(projectId)
      .then(setExportRecords)
      .catch(() => setExportRecords([]));
    loadWorkbenchSummary(projectId);
    loadConversionRuns(projectId);
  };

  const loadConverterSettings = () => {
    getConverterSettings()
      .then((settings) => {
        setConverterSettings(settings);
        const active = settings.find((item) => item.is_enabled) ?? settings[0];
        if (active) {
          setConverterName(active.converter_name);
          setConverterExePath(active.converter_exe_path);
          setConverterOutputVersion(active.output_version);
        }
      })
      .catch(() => setConverterSettings([]));
  };

  const loadConversionRuns = (projectId: number) => {
    listProjectConversionRuns(projectId)
      .then(setConversionRuns)
      .catch(() => setConversionRuns([]));
  };

  const loadProjectBackups = (projectId: number) => {
    listProjectBackups(projectId)
      .then(setBackupRecords)
      .catch(() => setBackupRecords([]));
  };

  const loadWorkbenchSummary = (projectId: number) => {
    getProjectWorkbenchSummary(projectId)
      .then(setWorkbenchSummary)
      .catch(() => setWorkbenchSummary(null));
  };

  const refreshProjectAfterImport = (projectId: number) => {
    loadProjectFiles(projectId);
    loadProjectSheets(projectId);
    loadWorkbenchSummary(projectId);
    loadConversionRuns(projectId);
    getProject(projectId)
      .then((project) => {
        setSelectedProject(project);
        setProjects((current) => current.map((item) => (item.id === project.id ? project : item)));
      })
      .catch(() => undefined);
    refreshProjects();
  };

  const scrollToConverterSettings = () => {
    document.querySelector(".converter-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const returnToProjectHome = () => {
    setImportOpen(false);
    document.querySelector(".project-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const updateSheetQuery = (patch: SheetQuery) => {
    if (!selectedProject) {
      return;
    }
    const next = { ...sheetQuery, ...patch, page: patch.page ?? 1 };
    setSheetQuery(next);
    loadProjectSheets(selectedProject.id, next);
  };

  const applyQuickFilter = (patch: SheetQuery) => {
    const reset: SheetQuery = {
      status: undefined,
      review_status: undefined,
      trust_level: undefined,
      source_format: undefined,
      issue_severity: undefined,
      issue_code: undefined,
      has_issue: undefined,
      has_error: undefined,
      has_warning: undefined,
      low_confidence: undefined,
      missing_field: undefined
    };
    updateSheetQuery({ ...reset, ...patch, page: 1 });
  };

  const openReviewFilter = (patch: SheetQuery) => {
    applyQuickFilter(patch);
    const target = sheets.find((sheet) => {
      if (patch.review_status && sheet.review_status !== patch.review_status) {
        return false;
      }
      if (patch.low_confidence && !["C", "D"].includes(sheet.trust_level ?? "")) {
        return false;
      }
      if (patch.missing_field === "drawing_no" && sheet.drawing_no) {
        return false;
      }
      if (patch.missing_field === "drawing_name" && sheet.drawing_name) {
        return false;
      }
      if (patch.has_error && sheet.error_count === 0) {
        return false;
      }
      if (patch.has_warning && sheet.warning_count === 0) {
        return false;
      }
      return true;
    });
    if (target) {
      openReviewWorkbench(target);
    }
  };

  const handleUpdateProject = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedProject) {
      return;
    }

    const trimmedName = editName.trim();
    if (!trimmedName) {
      setFormError("项目名称不能为空");
      return;
    }

    updateProject(selectedProject.id, {
      name: trimmedName,
      description: editDescription.trim() || undefined
    })
      .then((project) => {
        setSelectedProject(project);
        setProjects((current) =>
          current.map((item) => (item.id === project.id ? project : item))
        );
        setEditing(false);
        setFormError("");
      })
      .catch(() => setFormError("项目更新失败，请稍后重试"));
  };

  const handleDeleteProject = (projectId: number) => {
    deleteProject(projectId)
      .then(() => {
        setProjects((current) => current.filter((item) => item.id !== projectId));
        if (selectedProject?.id === projectId) {
          setSelectedProject(null);
          setWorkbenchSummary(null);
          setProjectFiles([]);
          setSheets([]);
          setSheetPage({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
          setBackupRecords([]);
          setBackupResult(null);
          setBackupError("");
          setRestoreResult(null);
          setVerifyResults({});
          setProjectHealthResult(null);
          setOrphanScanResult(null);
          setSelectedFiles([]);
          setSelectedRejectedFiles([]);
          setImportResult(null);
        }
      })
      .catch(() => setProjectError("项目删除失败"));
  };

  const handleSelectFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    const invalidFiles = files
      .filter((file) => !isSupportedDrawingFile(file.name))
      .map((file) => ({
        name: file.name,
        size: file.size,
        reason: "当前文件格式不支持，请导入 PDF、DXF 或 DWG 文件。"
      }));
    const drawingFiles = files.filter((file) => isSupportedDrawingFile(file.name));
    setSelectedFiles(drawingFiles);
    setSelectedRejectedFiles(invalidFiles);
    setImportResult(null);
    setImportError(
      invalidFiles.length > 0
        ? [
            "以下文件格式暂不支持，请移除后继续。",
            ...invalidFiles.map((file) => `${file.name}：${file.reason}`)
          ].join("\n")
        : ""
    );
  };

  const handleUpload = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedProject) {
      return;
    }
    if (selectedRejectedFiles.length > 0) {
      setImportError([
        "以下文件格式暂不支持，请移除后继续。",
        ...selectedRejectedFiles.map((file) => `${file.name}：${file.reason}`)
      ].join("\n"));
      return;
    }
    const oversizedFiles = selectedFiles.filter((file) => file.size > UPLOAD_MAX_BYTES);
    if (oversizedFiles.length > 0) {
      setImportError([
        "以下文件超过大小限制，请移除后继续。",
        ...oversizedFiles.map((file) => `${file.name}：${formatFileSize(file.size)}，上限 ${formatFileSize(UPLOAD_MAX_BYTES)}`)
      ].join("\n"));
      return;
    }
    if (selectedFiles.length === 0) {
      setImportError([
        "操作失败",
        "错误码：NO_DRAWING_FILE_SELECTED",
        "说明：请选择至少一个 PDF、DXF 或 DWG 文件。",
        "建议：点击文件选择框后选择图纸文件，再开始导入。"
      ].join("\n"));
      return;
    }

    uploadProjectPdfs(selectedProject.id, {
      batchName,
      remark,
      files: selectedFiles
    })
      .then((result) => {
        setImportResult(result);
        setImportError("");
        setSelectedFiles([]);
        setSelectedRejectedFiles([]);
        setBatchName("");
        setRemark("");
        refreshProjectAfterImport(selectedProject.id);
      })
      .catch((error) => setImportError(formatApiError(error, "导入失败，请确认文件格式和本地服务状态")));
  };

  const handleSplitBatch = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    splitImportBatch(batchId)
      .then((result) => {
        setSplitResult(result);
        setSplitError("");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        refreshProjects();
      })
      .catch((error) => setSplitError(formatApiError(error, "生成图纸页预览失败，请稍后重试")));
  };

  const handlePrepareDxfSheet = (fileId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`prepare-${fileId}`);
    prepareDxfSheet(fileId)
      .then((result) => {
        setDxfPrepareResult(result);
        setBatchDxfPrepareResult(null);
        setDxfPrepareError("");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        refreshProjects();
      })
      .catch((error) => setDxfPrepareError(formatApiError(error, "准备 DXF 图纸页失败，请稍后重试")))
      .finally(() => setBusyAction(""));
  };

  const handlePrepareBatchDxfSheets = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`prepare-batch-${batchId}`);
    prepareDxfSheetsForBatch(batchId)
      .then((result) => {
        setBatchDxfPrepareResult(result);
        setDxfPrepareResult(null);
        setDxfPrepareError("");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        refreshProjects();
      })
      .catch((error) => setDxfPrepareError(formatApiError(error, "批量准备 DXF 图纸页失败，请稍后重试")))
      .finally(() => setBusyAction(""));
  };

  const handleParseDxfFile = (fileId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`parse-${fileId}`);
    parseDxfFile(fileId)
      .then((result) => {
        setCadParseResult(result);
        setBatchCadParseResult(null);
        setCadParseError("");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        refreshProjects();
      })
      .catch((error) => setCadParseError(formatApiError(error, "解析 DXF 失败，请稍后重试")))
      .finally(() => setBusyAction(""));
  };

  const handleParseDxfBatch = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`parse-batch-${batchId}`);
    parseDxfBatch(batchId)
      .then((result) => {
        setBatchCadParseResult(result);
        setCadParseResult(null);
        setCadParseError("");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        refreshProjects();
      })
      .catch((error) => setCadParseError(formatApiError(error, "批量解析 DXF 失败，请稍后重试")))
      .finally(() => setBusyAction(""));
  };

  const handleLoadCadParseSummary = (sheetId: number) => {
    setBusyAction(`cad-summary-${sheetId}`);
    setCadParseError("");
    getCadParseSummary(sheetId)
      .then((result) => {
        setCadParseSummary(result);
        setCadParseError("");
      })
      .catch((error) => setCadParseError(formatApiError(error, "未找到 CAD 解析结果，请先执行 DXF 解析")))
      .finally(() => setBusyAction(""));
  };

  const handleGenerateCadPreview = (sheetId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`cad-preview-${sheetId}`);
    setCadPreviewError("");
    generateCadPreview(sheetId)
      .then((result) => {
        setCadPreviewResult(result);
        setBatchCadPreviewResult(null);
        setCadPreviewError("");
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        getSheet(sheetId).then((sheet) => {
          setDetailSheet((current) => (current?.id === sheetId ? sheet : current));
          setPreviewSheet((current) => (current?.id === sheetId ? sheet : current));
        });
      })
      .catch((error) => setCadPreviewError(formatApiError(error, "CAD 图形预览生成失败")))
      .finally(() => setBusyAction(""));
  };

  const cadPreviewBatchPayload = (): CadPreviewBatchPayload => ({
    skip_completed: cadPreviewSkipCompleted,
    force: cadPreviewForce,
    continue_on_error: cadPreviewContinueOnError
  });

  const handleGenerateBatchCadPreview = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`cad-preview-batch-${batchId}`);
    setCadPreviewError("");
    generateBatchCadPreview(batchId, cadPreviewBatchPayload())
      .then((result) => {
        setBatchCadPreviewResult(result);
        setCadPreviewResult(null);
        setCadPreviewError("");
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
      })
      .catch((error) => setCadPreviewError(formatApiError(error, "批量生成 CAD 图形预览失败")))
      .finally(() => setBusyAction(""));
  };

  const handleGenerateProjectCadPreview = (projectId: number) => {
    setBusyAction(`cad-preview-project-${projectId}`);
    setCadPreviewError("");
    generateProjectCadPreview(projectId, cadPreviewBatchPayload())
      .then((result) => {
        setBatchCadPreviewResult(result);
        setCadPreviewResult(null);
        setCadPreviewError("");
        loadProjectSheets(projectId);
        loadWorkbenchSummary(projectId);
      })
      .catch((error) => setCadPreviewError(formatApiError(error, "项目级批量生成 CAD 图形预览失败")))
      .finally(() => setBusyAction(""));
  };

  const handleSaveConverterSettings = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const active = converterSettings.find((item) => item.is_enabled) ?? converterSettings[0];
    saveConverterSettings(
      {
        converter_name: converterName.trim() || "ODA File Converter",
        converter_exe_path: converterExePath.trim(),
        output_version: converterOutputVersion.trim() || "ACAD2018",
        output_type: "DXF",
        is_enabled: true
      },
      active?.id
    )
      .then((setting) => {
        setConverterSettings((current) => {
          const existing = current.some((item) => item.id === setting.id);
          return existing
            ? current.map((item) => (item.id === setting.id ? setting : item))
            : [setting, ...current];
        });
        setConverterMessage("转换工具配置已保存。");
        setConverterError("");
      })
      .catch((error) => setConverterError(formatApiError(error, "保存转换工具配置失败")));
  };

  const handleCheckConverter = () => {
    const active = converterSettings.find((item) => item.is_enabled) ?? converterSettings[0];
    if (!active) {
      setConverterError("请先保存转换工具配置。");
      return;
    }
    setBusyAction(`check-converter-${active.id}`);
    checkConverterSetting(active.id)
      .then((result) => {
        setConverterMessage(result.message);
        setConverterError("");
        loadConverterSettings();
      })
      .catch((error) => setConverterError(formatApiError(error, "转换工具检测失败")))
      .finally(() => setBusyAction(""));
  };

  const handleConvertDwgFile = (fileId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`convert-${fileId}`);
    convertDwgFile(fileId)
      .then((result) => {
        setDwgConvertResult(result);
        setBatchDwgConvertResult(null);
        setConverterError(result.status === "failed" ? `${result.error_code}：${result.error_message}` : "");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        loadConversionRuns(selectedProject.id);
      })
      .catch((error) => setConverterError(formatApiError(error, "DWG 转 DXF 失败")))
      .finally(() => setBusyAction(""));
  };

  const handleConvertDwgBatch = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`convert-batch-${batchId}`);
    convertDwgBatch(batchId)
      .then((result) => {
        setBatchDwgConvertResult(result);
        setDwgConvertResult(null);
        setConverterError(result.failed_count > 0 ? "部分 DWG 转换失败，请查看转换历史。" : "");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        loadConversionRuns(selectedProject.id);
      })
      .catch((error) => setConverterError(formatApiError(error, "批量 DWG 转 DXF 失败")))
      .finally(() => setBusyAction(""));
  };

  const toggleCadPipelineStep = (step: CadPipelineStep) => {
    setCadPipelineSteps((current) =>
      current.includes(step)
        ? current.filter((item) => item !== step)
        : [...current, step]
    );
  };

  const stopCadPipelinePolling = React.useCallback(() => {
    if (cadPipelineJobPollRef.current !== null) {
      window.clearInterval(cadPipelineJobPollRef.current);
      cadPipelineJobPollRef.current = null;
    }
  }, []);

  React.useEffect(() => {
    return () => {
      stopCadPipelinePolling();
    };
  }, [stopCadPipelinePolling]);

  const finalizeCadPipelineJob = React.useCallback(
    (job: BackgroundJobStatus) => {
      stopCadPipelinePolling();
      setCadPipelineJob(job);
      setCadPipelineStartedAt(null);
      setBusyAction("");
      const projectId = cadPipelineProjectIdRef.current;
      if (job.result_summary) {
        setCadPipelineResult(job.result_summary);
        setCadPipelineElapsed(job.result_summary.summary.duration_seconds);
      }
      if (job.status === "failed") {
        setCadPipelineError(job.message || "CAD 批量处理失败。");
      } else {
        setCadPipelineError("");
      }
      if (projectId !== null) {
        loadProjectFiles(projectId);
        loadProjectSheets(projectId);
        loadWorkbenchSummary(projectId);
        loadConversionRuns(projectId);
        refreshProjects();
      }
    },
    [
      loadConversionRuns,
      loadProjectFiles,
      loadProjectSheets,
      refreshProjects,
      stopCadPipelinePolling
    ]
  );

  const handleRunCadPipeline = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    if (cadPipelineSteps.length === 0) {
      setCadPipelineError([
        "操作失败",
        "错误码：NO_CAD_PIPELINE_STEP_SELECTED",
        "说明：请选择至少一个 CAD 批量处理步骤。",
        "建议：勾选 DWG 转换、DXF 解析、生成候选值或 CAD 预览后再运行。"
      ].join("\n"));
      return;
    }
    const hasActiveConverter = converterSettings.some((item) => item.is_enabled);
    if (cadPipelineSteps.includes("convert_dwg") && dwgFileCount > 0 && !hasActiveConverter) {
      setCadPipelineError([
        "操作失败",
        "错误码：CONVERTER_NOT_CONFIGURED",
        "说明：尚未配置 DWG 转 DXF 工具。",
        "建议：先在 CAD 转换设置中保存并检测转换工具。"
      ].join("\n"));
      return;
    }
    const payload: CadPipelineRequest = {
      steps: cadPipelineSteps,
      skip_completed: cadPipelineSkipCompleted,
      continue_on_error: cadPipelineContinueOnError
    };
    setBusyAction(`cad-pipeline-${batchId}`);
    const startedAt = Date.now();
    setCadPipelineStartedAt(startedAt);
    setCadPipelineElapsed(0);
    setCadPipelineResult(null);
    setCadPipelineJob(null);
    setCadPipelineError("");
    cadPipelineProjectIdRef.current = selectedProject.id;
    stopCadPipelinePolling();

    startCadPipeline(batchId, payload)
      .then((initial) => {
        setCadPipelineJob(initial);
        if (initial.status !== "running") {
          finalizeCadPipelineJob(initial);
          return;
        }
        cadPipelineJobPollRef.current = window.setInterval(() => {
          getCadPipelineJob(batchId)
            .then((job) => {
              if (job === null) {
                return;
              }
              setCadPipelineJob(job);
              if (job.status !== "running") {
                finalizeCadPipelineJob(job);
              }
            })
            .catch((error) => {
              stopCadPipelinePolling();
              setCadPipelineError(formatApiError(error, "无法获取 CAD 流水线进度"));
              setCadPipelineStartedAt(null);
              setBusyAction("");
            });
        }, 2000);
      })
      .catch((error) => {
        setCadPipelineError(formatApiError(error, "CAD 批量处理启动失败"));
        setCadPipelineStartedAt(null);
        setBusyAction("");
      });
  };

  const handleCropSheetTitle = (sheetId: number) => {
    if (!selectedProject) {
      return;
    }
    cropSheetTitle(sheetId)
      .then((result) => {
        setTitleCropError("");
        updateSheetTitleCrop(result);
        loadProjectSheets(selectedProject.id);
      })
      .catch((error) => setTitleCropError(formatApiError(error, "生成标题栏裁剪图失败，请稍后重试")));
  };

  const handleCropBatchTitles = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    cropBatchTitles(batchId)
      .then((result) => {
        setTitleCropResult(result);
        setTitleCropError("");
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
      })
      .catch((error) => setTitleCropError(formatApiError(error, "批量生成标题栏裁剪图失败，请稍后重试")));
  };

  const handleExtractSheetText = (sheetId: number) => {
    extractSheetText(sheetId)
      .then((result) => {
        setRecognitionError("");
        setRecognitionResult(singleRecognitionAsBatch(result, latestBatchId ?? 0));
      })
      .catch((error) => setRecognitionError(formatApiError(error, "PDF 文本提取失败，请稍后重试")));
  };

  const handleOcrSheetTitle = (sheetId: number) => {
    ocrSheetTitle(sheetId)
      .then((result) => {
        setRecognitionError("");
        setRecognitionResult(singleRecognitionAsBatch(result, latestBatchId ?? 0));
      })
      .catch((error) => setRecognitionError(formatApiError(error, "标题栏 OCR 失败，请确认已生成标题栏裁剪图")));
  };

  const handleExtractBatchText = (batchId: number) => {
    extractBatchText(batchId)
      .then((result) => {
        setRecognitionResult(result);
        setRecognitionError("");
      })
      .catch((error) => setRecognitionError(formatApiError(error, "批量 PDF 文本提取失败，请稍后重试")));
  };

  const stopOcrJobPolling = React.useCallback(() => {
    if (ocrJobPollRef.current !== null) {
      window.clearInterval(ocrJobPollRef.current);
      ocrJobPollRef.current = null;
    }
  }, []);

  React.useEffect(() => stopOcrJobPolling, [stopOcrJobPolling]);

  const handleOcrBatchTitles = (batchId: number) => {
    stopOcrJobPolling();
    ocrBatchTitles(batchId)
      .then((job) => {
        setOcrJob(job);
        setRecognitionError("");
        if (job.status === "running") {
          ocrJobPollRef.current = window.setInterval(() => {
            getOcrBatchJob(batchId)
              .then((next) => {
                setOcrJob(next);
                if (next.status === "completed" || next.status === "failed") {
                  stopOcrJobPolling();
                  if (next.status === "failed" && next.message) {
                    setRecognitionError(`批量 OCR 失败：${next.message}`);
                  }
                }
              })
              .catch(() => {
                stopOcrJobPolling();
                setRecognitionError([
                  "操作失败",
                  "错误码：OCR_JOB_POLL_FAILED",
                  "说明：批量 OCR 进度查询失败。",
                  "建议：请确认后端服务仍在运行，稍后刷新项目状态。"
                ].join("\n"));
              });
          }, 2000);
        } else if (job.status === "failed" && job.message) {
          setRecognitionError(`批量 OCR 失败：${job.message}`);
        }
      })
      .catch((error) => setRecognitionError(formatApiError(error, "批量标题栏 OCR 失败，请确认已生成标题栏裁剪图")));
  };

  const handleLoadRuns = (sheetId: number) => {
    listRecognitionRuns(sheetId)
      .then((runs) => {
        setRecognitionRuns(runs);
        setRunsSheetId(sheetId);
        setRecognitionError("");
      })
      .catch((error) => setRecognitionError(formatApiError(error, "识别运行记录加载失败")));
  };

  const handleGenerateSheetCandidates = (sheetId: number) => {
    setBusyAction(`candidates-${sheetId}`);
    generateSheetCandidates(sheetId)
      .then((result) => {
        setCandidateResult({
          batch_id: latestBatchId ?? 0,
          total_count: 1,
          success_count: 1,
          failed_count: 0,
          candidate_count: result.candidate_count,
          items: [result]
        });
        setCandidates(result.candidates);
        setCandidatesSheetId(sheetId);
        setCandidateError("");
        if (selectedProject) {
          loadWorkbenchSummary(selectedProject.id);
        }
      })
      .catch((error) => setCandidateError(formatApiError(error, "候选值生成失败。DXF 请先解析 DXF，再生成候选值。PDF 请先完成文本提取或 OCR 原始结果")))
      .finally(() => setBusyAction(""));
  };

  const handleGenerateBatchCandidates = (batchId: number) => {
    generateBatchCandidates(batchId)
      .then((result) => {
        setCandidateResult(result);
        setCandidateError("");
        if (selectedProject) {
          loadWorkbenchSummary(selectedProject.id);
        }
      })
      .catch((error) => setCandidateError(formatApiError(error, "批量生成候选值失败")));
  };

  const handleLoadCandidates = (sheetId: number) => {
    listSheetCandidates(sheetId)
      .then((data) => {
        setCandidates(data);
        setCandidatesSheetId(sheetId);
        setCandidateError("");
      })
      .catch((error) => setCandidateError(formatApiError(error, "候选值加载失败")));
  };

  const handleFuseSheetFields = (sheetId: number) => {
    if (!selectedProject) {
      return;
    }
    setBusyAction(`fusion-${sheetId}`);
    fuseSheetFields(sheetId)
      .then((result) => {
        setFusionResult({
          batch_id: latestBatchId ?? 0,
          total_count: 1,
          success_count: 1,
          failed_count: 0,
          issue_count: result.issues.length,
          items: [result]
        });
        setFieldValues(result.field_values);
        setFieldValuesSheetId(sheetId);
        setFusionError("");
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
      })
      .catch((error) => setFusionError(formatApiError(error, "生成推荐字段失败，请确认已生成候选值")))
      .finally(() => setBusyAction(""));
  };

  const handleFuseBatchFields = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    fuseBatchFields(batchId)
      .then((result) => {
        setFusionResult(result);
        setFusionError("");
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
        refreshProjects();
      })
      .catch((error) => setFusionError(formatApiError(error, "批量生成推荐字段失败")));
  };

  const handleLoadFieldValues = (sheetId: number) => {
    Promise.all([listSheetFieldValues(sheetId), listSheetEvidence(sheetId)])
      .then(([values, evidence]) => {
        setFieldValues(values);
        setFieldEvidence(evidence);
        setFieldValuesSheetId(sheetId);
        setFusionError("");
      })
      .catch((error) => setFusionError(formatApiError(error, "推荐字段或证据加载失败")));
  };

  const handleOpenSheetDetail = (sheetId: number) => {
    getSheet(sheetId)
      .then((sheet) => {
        setDetailSheet(sheet);
        setPreviewSheet(sheet);
        handleLoadCandidates(sheetId);
        handleLoadRuns(sheetId);
        handleLoadFieldValues(sheetId);
      })
      .catch((error) => setFusionError(formatApiError(error, "图纸详情加载失败")));
  };

  const openReviewWorkbench = (sheet: DrawingSheet) => {
    setReviewSheet(sheet);
    setReviewFields({
      drawing_no: sheet.drawing_no ?? "",
      drawing_name: sheet.drawing_name ?? "",
      discipline: sheet.discipline ?? "",
      version: sheet.version ?? "",
      issue_date: sheet.issue_date ?? ""
    });
    setReviewNote("");
    setReviewError("");
    setReviewMessage("");
    handleLoadCandidates(sheet.id);
    handleLoadRuns(sheet.id);
    handleLoadFieldValues(sheet.id);
    getSheetAuditLogs(sheet.id).then(setAuditLogs).catch(() => setAuditLogs([]));
  };

  const refreshReviewContext = (sheetId: number) => {
    if (selectedProject) {
      loadProjectSheets(selectedProject.id);
      loadWorkbenchSummary(selectedProject.id);
    }
    getSheet(sheetId).then((sheet) => {
      setReviewSheet(sheet);
      setReviewFields({
        drawing_no: sheet.drawing_no ?? "",
        drawing_name: sheet.drawing_name ?? "",
        discipline: sheet.discipline ?? "",
        version: sheet.version ?? "",
        issue_date: sheet.issue_date ?? ""
      });
    });
    handleLoadFieldValues(sheetId);
    getSheetAuditLogs(sheetId).then(setAuditLogs).catch(() => setAuditLogs([]));
  };

  const handleSaveReviewFields = () => {
    if (!reviewSheet) {
      return;
    }
    setReviewSaveState("saving");
    setReviewMessage("保存中...");
    updateSheetFields(reviewSheet.id, { fields: reviewFields, note: reviewNote })
      .then(() => {
        setReviewSaveState("success");
        setReviewMessage("保存成功，已自动记录修改日志");
        setReviewError("");
        refreshReviewContext(reviewSheet.id);
      })
      .catch((error) => {
        setReviewSaveState("failed");
        setReviewError(formatApiError(error, "SAVE_FAILED：字段保存失败"));
      });
  };

  const handleAdoptCandidate = (candidate: RecognitionCandidate) => {
    if (!reviewSheet) {
      return;
    }
    adoptCandidate(reviewSheet.id, candidate.id, "采用候选值")
      .then(() => {
        setReviewMessage("候选值已采用");
        setReviewError("");
        refreshReviewContext(reviewSheet.id);
      })
      .catch((error) => setReviewError(formatApiError(error, "采用候选值失败")));
  };

  const handleApplyCandidateValue = (candidate: RecognitionCandidate) => {
    const value = candidate.normalized_value || candidate.candidate_value;
    setReviewFields({ ...reviewFields, [candidate.field_name]: value });
    setReviewMessage("候选值已填入，保存后会记录审计日志");
  };

  const handleAdoptRecommendedField = (fieldName: string) => {
    const recommended = recommendedCandidate(fieldName, candidates);
    if (recommended) {
      handleApplyCandidateValue(recommended);
    }
  };

  const handleClearReviewField = (fieldName: string) => {
    setReviewFields({ ...reviewFields, [fieldName]: "" });
    setReviewMessage("字段已清空，保存后会记录审计日志");
  };

  const handleRestoreRecommendedField = (fieldName: string) => {
    if (!reviewSheet) {
      return;
    }
    restoreRecommendedField(reviewSheet.id, fieldName, "恢复机器推荐值")
      .then(() => {
        setReviewMessage("已恢复机器推荐值");
        setReviewError("");
        refreshReviewContext(reviewSheet.id);
      })
      .catch((error) => setReviewError(formatApiError(error, "RESTORE_RECOMMENDED_FAILED：恢复机器推荐值失败")));
  };

  const handleConfirmReviewSheet = () => {
    if (!reviewSheet) {
      return;
    }
    confirmSheet(reviewSheet.id, { force: false, note: reviewNote })
      .then(() => {
        setReviewMessage("图纸已确认");
        setReviewError("");
        refreshReviewContext(reviewSheet.id);
      })
      .catch((error) => setReviewError(formatApiError(error, "存在阻断问题，暂不能确认")));
  };

  const handleSaveAndConfirmReviewSheet = () => {
    if (!reviewSheet) {
      return;
    }
    setReviewSaveState("saving");
    setReviewMessage("保存中...");
    updateSheetFields(reviewSheet.id, { fields: reviewFields, note: reviewNote })
      .then(() => confirmSheet(reviewSheet.id, { force: false, note: reviewNote }))
      .then(() => {
        setReviewSaveState("success");
        setReviewMessage("保存成功，图纸已确认，已自动记录修改日志");
        setReviewError("");
        refreshReviewContext(reviewSheet.id);
      })
      .catch((error) => {
        setReviewSaveState("failed");
        setReviewError(formatApiError(error, "SAVE_OR_CONFIRM_FAILED：保存或确认失败"));
      });
  };

  const handleUpdateIssueStatus = (issueId: number, status: string) => {
    if (!reviewSheet) {
      return;
    }
    updateIssue(issueId, { status, note: reviewNote })
      .then(() => {
        setReviewMessage("问题状态已更新");
        setReviewError("");
        refreshReviewContext(reviewSheet.id);
      })
      .catch((error) => setReviewError(formatApiError(error, "问题状态更新失败")));
  };

  const handleBatchConfirm = (
    confirmMode = "selected",
    source: "filtered" | "manual" = "filtered"
  ) => {
    if (!selectedProject) {
      return;
    }
    const ids = source === "manual" ? selectedSheetIds : sheets.map((sheet) => sheet.id);
    if (ids.length === 0) {
      setReviewError([
        "操作失败",
        "错误码：NO_SHEET_SELECTED",
        `说明：${source === "manual" ? "请先勾选要批量确认的图纸。" : "当前筛选结果为空。"}`,
        "建议：选择图纸或调整筛选条件后再批量确认。"
      ].join("\n"));
      return;
    }
    batchConfirmProject(selectedProject.id, {
      sheet_ids: ids,
      confirm_mode: confirmMode,
      only_without_errors: true,
      note: source === "manual" ? "批量确认手动勾选图纸" : "批量确认当前筛选结果"
    })
      .then((result) => {
        setBatchConfirmResult(result);
        loadProjectSheets(selectedProject.id);
        loadWorkbenchSummary(selectedProject.id);
      })
      .catch((error) => setReviewError(formatApiError(error, "批量确认失败")));
  };

  const toggleSelectedSheet = (sheetId: number) => {
    setSelectedSheetIds((current) =>
      current.includes(sheetId) ? current.filter((id) => id !== sheetId) : [...current, sheetId]
    );
  };

  const toggleCurrentPageSelection = () => {
    const pageIds = sheets.map((sheet) => sheet.id);
    const allSelected = pageIds.length > 0 && pageIds.every((id) => selectedSheetIds.includes(id));
    setSelectedSheetIds((current) =>
      allSelected
        ? current.filter((id) => !pageIds.includes(id))
        : Array.from(new Set([...current, ...pageIds]))
    );
  };

  const handleCheckExport = () => {
    if (!selectedProject) {
      return;
    }
    checkExport(selectedProject.id)
      .then((result) => {
        setExportCheck(result);
        setExportError("");
      })
      .catch((error) => setExportError(formatApiError(error, "导出前检查失败")));
  };

  const handleExportExcel = (confirmIncomplete: boolean) => {
    if (!selectedProject) {
      return;
    }
    exportExcel(selectedProject.id, {
      confirm_incomplete: confirmIncomplete,
      include_issues: true,
      filter: null
    })
      .then((result) => {
        setExportResult(result);
        setExportError("");
        loadWorkbenchSummary(selectedProject.id);
        listExports(selectedProject.id).then(setExportRecords);
      })
      .catch((error) => setExportError(formatApiError(error, "导出失败：项目无图纸、导出目录不可写或 Excel 文件写入失败")));
  };

  const handleCreateBackup = () => {
    if (!selectedProject) {
      return;
    }
    setBackupBusy(true);
    createProjectBackup(selectedProject.id)
      .then((result) => {
        setBackupResult(result);
        setBackupError("");
        loadWorkbenchSummary(selectedProject.id);
        loadProjectBackups(selectedProject.id);
      })
      .catch((error) => setBackupError(formatApiError(error, "项目备份创建失败，请稍后重试")))
      .finally(() => setBackupBusy(false));
  };

  const handleRestoreBackup = (backupId: number) => {
    const confirmed = window.confirm("恢复备份会创建一个新项目，不会覆盖当前已有项目。是否继续？");
    if (!confirmed) {
      return;
    }
    setRestoreBusyId(backupId);
    restoreBackupAsNewProject(backupId)
      .then((result) => {
        setRestoreResult(result);
        setBackupError("");
        refreshProjects();
      })
      .catch((error) => setBackupError(formatApiError(error, "恢复失败，请检查备份包是否完整")))
      .finally(() => setRestoreBusyId(null));
  };

  const handleDeleteBackup = (backupId: number) => {
    const confirmed = window.confirm("删除备份只会删除备份包和记录，不会删除项目。是否继续？");
    if (!confirmed || !selectedProject) {
      return;
    }
    setDeleteBackupBusyId(backupId);
    deleteBackup(backupId)
      .then(() => {
        setBackupRecords((current) => current.filter((item) => item.backup_id !== backupId));
        if (backupResult?.backup_id === backupId) {
          setBackupResult(null);
        }
        setBackupError("");
      })
      .catch((error) => setBackupError(formatApiError(error, "备份删除失败")))
      .finally(() => setDeleteBackupBusyId(null));
  };

  const handleVerifyBackup = (backupId: number) => {
    setVerifyBusyId(backupId);
    verifyBackup(backupId)
      .then((result) => {
        setVerifyResults((current) => ({ ...current, [backupId]: result }));
        setBackupError("");
      })
      .catch((error) => setBackupError(formatApiError(error, "备份包校验失败")))
      .finally(() => setVerifyBusyId(null));
  };

  const handleRunSystemHealthCheck = () => {
    setMaintenanceBusy("system-health");
    setMaintenanceError("");
    runSystemHealthCheck()
      .then((result) => {
        setSystemHealthResult(result);
        setMaintenanceReportResult(null);
      })
      .catch((error) => setMaintenanceError(formatApiError(error, "系统健康检查失败")))
      .finally(() => setMaintenanceBusy(""));
  };

  const handleRunProjectHealthCheck = () => {
    if (!selectedProject) {
      return;
    }
    setMaintenanceBusy("project-health");
    setMaintenanceError("");
    runProjectHealthCheck(selectedProject.id)
      .then((result) => {
        setProjectHealthResult(result);
        setOrphanScanResult(null);
        loadWorkbenchSummary(selectedProject.id);
      })
      .catch((error) => setMaintenanceError(formatApiError(error, "项目完整性检查失败")))
      .finally(() => setMaintenanceBusy(""));
  };

  const handleScanOrphanFiles = () => {
    if (!selectedProject) {
      return;
    }
    setMaintenanceBusy("orphan-scan");
    setMaintenanceError("");
    scanProjectOrphanFiles(selectedProject.id)
      .then(setOrphanScanResult)
      .catch((error) => setMaintenanceError(formatApiError(error, "孤儿文件扫描失败")))
      .finally(() => setMaintenanceBusy(""));
  };

  const handleCleanupTempFiles = () => {
    setMaintenanceBusy("cleanup-temp");
    setMaintenanceError("");
    cleanupTempFiles()
      .then((result) => {
        setTempCleanupResult(result);
        getDataSafetySummary().then(setDataSafetySummary).catch(() => setDataSafetySummary(null));
      })
      .catch((error) => setMaintenanceError(formatApiError(error, "临时文件清理失败")))
      .finally(() => setMaintenanceBusy(""));
  };

  const handleBuildMaintenanceReport = () => {
    setMaintenanceBusy("maintenance-report");
    setMaintenanceError("");
    buildMaintenanceReport()
      .then((result) => {
        setMaintenanceReportResult(result);
        setSystemHealthResult(result.system_health);
      })
      .catch((error) => setMaintenanceError(formatApiError(error, "维护报告生成失败")))
      .finally(() => setMaintenanceBusy(""));
  };

  const updateSheetTitleCrop = (result: TitleCropResult) => {
    setSheets((current) =>
      current.map((sheet) =>
        sheet.id === result.sheet_id
          ? {
              ...sheet,
              title_crop_path: result.title_crop_path,
              title_crop_status: result.status,
              title_crop_error_code: result.error_code,
              title_crop_error_message: result.error_message
            }
          : sheet
      )
    );
    setPreviewSheet((current) =>
      current?.id === result.sheet_id
        ? {
            ...current,
            title_crop_path: result.title_crop_path,
            title_crop_status: result.status,
            title_crop_error_code: result.error_code,
            title_crop_error_message: result.error_message
          }
        : current
    );
  };

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!reviewSheet || event.isComposing) {
        return;
      }
      if (event.ctrlKey && event.key.toLowerCase() === "s") {
        event.preventDefault();
        handleSaveReviewFields();
      }
      if (event.ctrlKey && event.key === "Enter") {
        event.preventDefault();
        handleSaveAndConfirmReviewSheet();
      }
      if (event.altKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        const currentIndex = sheets.findIndex((sheet) => sheet.id === reviewSheet.id);
        const next = sheets[currentIndex + 1] ?? sheets.find((sheet) => sheet.id !== reviewSheet.id);
        if (next) {
          openReviewWorkbench(next);
        }
      }
      if (event.altKey && event.key.toLowerCase() === "p") {
        event.preventDefault();
        const currentIndex = sheets.findIndex((sheet) => sheet.id === reviewSheet.id);
        const previous = sheets[currentIndex - 1];
        if (previous) {
          openReviewWorkbench(previous);
        }
      }
      if (event.key === "Escape") {
        setReviewSheet(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [reviewSheet, reviewFields, reviewNote, sheets]);

  const latestBatchId = importResult?.id ?? projectFiles[0]?.batch_id;
  const selectedFileTypeCounts = selectedFiles.reduce(
    (counts, file) => {
      counts[drawingFileKind(file.name)] += 1;
      return counts;
    },
    { pdf: 0, dxf: 0, dwg: 0, unsupported: selectedRejectedFiles.length } as Record<DrawingFileKind, number>
  );
  const selectedTotalSize =
    selectedFiles.reduce((total, file) => total + file.size, 0) +
    selectedRejectedFiles.reduce((total, file) => total + file.size, 0);
  const selectedOversizedFiles = selectedFiles.filter((file) => file.size > UPLOAD_MAX_BYTES);
  const selectedDuplicateNames = duplicateSelectedNames(selectedFiles);
  const existingDuplicateNames = existingProjectFileMatches(selectedFiles, projectFiles);
  const hasActiveConverter = converterSettings.some((item) => item.is_enabled);
  const pdfFileCount = projectFiles.filter((file) => file.source_format === "pdf").length;
  const dxfFileCount = projectFiles.filter((file) => file.source_format === "dxf").length;
  const dwgFileCount = projectFiles.filter((file) => file.source_format === "dwg").length;
  const convertedDwgCount = projectFiles.filter(
    (file) => file.source_format === "dwg" && file.convert_status === "success"
  ).length;
  const pendingDwgFiles = projectFiles.filter(
    (file) => file.source_format === "dwg" && file.convert_status !== "success"
  );
  const pendingDxfFiles = projectFiles.filter(
    (file) => file.source_format === "dxf" && file.status === "imported"
  );
  const dxfSheetCount = sheets.filter((sheet) => sheet.source_format === "dxf").length;
  const dxfParsedCount = sheets.filter((sheet) => sheet.source_format === "dxf" && ["cad_parsed", "recognized", "need_review", "confirmed"].includes(sheet.status)).length;
  const dxfFailedCount = sheets.filter((sheet) => sheet.source_format === "dxf" && sheet.status === "failed").length;
  const dxfRecommendedCount = sheets.filter((sheet) => sheet.source_format === "dxf" && ["recognized", "need_review", "confirmed"].includes(sheet.status)).length;
  const sheetByFileId = new Map(sheets.map((sheet) => [sheet.file_id, sheet]));
  const unsplitFileCount = projectFiles.filter(
    (file) => file.source_format === "pdf" && file.page_count === 0
  ).length;
  const preprocessedCount = sheets.filter((sheet) => sheet.status === "preprocessed").length;
  const failedSheetCount = sheets.filter((sheet) => sheet.status === "failed").length;
  const titleCroppedCount = sheets.filter((sheet) => sheet.title_crop_status === "success").length;
  const recommendedCount = sheets.filter((sheet) =>
    ["recognized", "need_review"].includes(sheet.status)
  ).length;
  const issueSummary = {
    error: sheets.reduce((total, sheet) => total + sheet.error_count, 0),
    warning: sheets.reduce((total, sheet) => total + sheet.warning_count, 0),
    info: sheets.reduce((total, sheet) => total + sheet.info_count, 0),
    missingDrawingNo: sheets.filter((sheet) => !sheet.drawing_no).length,
    missingDrawingName: sheets.filter((sheet) => !sheet.drawing_name).length,
    lowConfidence: sheets.filter((sheet) => ["C", "D"].includes(sheet.trust_level ?? "")).length,
    ocrEmpty: issues.filter((issue) => issue.issue_code === "OCR_TEXT_EMPTY").length,
    cadBlockAttrMissing: issues.filter((issue) => issue.issue_code === "CAD_BLOCK_ATTR_MISSING").length
  };
  const summarySheetCount = workbenchSummary?.drawing_sheet_count ?? selectedProject?.stats.sheet_count ?? 0;
  const summaryFileCount = workbenchSummary?.drawing_file_count ?? projectFiles.length;
  const summaryUnreviewedCount = workbenchSummary?.unreviewed_count ?? selectedProject?.stats.need_review_count ?? 0;
  const summaryLowConfidenceCount = workbenchSummary?.low_confidence_count ?? issueSummary.lowConfidence;
  const summaryMissingDrawingNoCount = workbenchSummary?.missing_drawing_no_count ?? issueSummary.missingDrawingNo;
  const summaryMissingDrawingNameCount = workbenchSummary?.missing_drawing_name_count ?? issueSummary.missingDrawingName;
  const summaryOpenErrorCount = workbenchSummary?.open_error_count ?? selectedProject?.stats.error_issue_count ?? issueSummary.error;
  const summaryOpenWarningCount = workbenchSummary?.open_warning_count ?? selectedProject?.stats.warning_issue_count ?? issueSummary.warning;
  const fallbackCadPreviewMissingCount = sheets.filter(
    (sheet) =>
      ["dxf", "dwg"].includes(sheet.source_format) &&
      (!sheet.cad_preview_path || sheet.cad_preview_status !== "success")
  ).length;
  const summaryCadPreviewMissingCount = workbenchSummary?.cad_preview_missing_count ?? fallbackCadPreviewMissingCount;
  const hasDxfWorkPending =
    pendingDxfFiles.length > 0 ||
    pendingDwgFiles.length > 0 ||
    projectFiles.some((file) => file.source_format === "dwg" && file.convert_status === "success" && file.status === "imported") ||
    sheets.some((sheet) => sheet.source_format === "dxf" && sheet.status === "cad_pending");
  const hasCandidatePending = sheets.some((sheet) =>
    ["preprocessed", "cad_pending", "cad_parsed"].includes(sheet.status)
  );
  const canRunCadPipeline = Boolean(latestBatchId && (dxfFileCount > 0 || dwgFileCount > 0 || convertedDwgCount > 0));
  const canGenerateCadPreview =
    summaryCadPreviewMissingCount > 0;
  const canExportProject = summarySheetCount > 0;
  const canBackupProject = Boolean(selectedProject);
  const nextStep = (() => {
    if (projectFiles.length === 0 && summarySheetCount === 0) {
      return {
        message: "当前项目还没有图纸。建议先导入 PDF、DXF 或 DWG 文件。",
        actions: [{ label: "导入图纸", onClick: () => setImportOpen(true), primary: true }]
      };
    }
    if (unsplitFileCount > 0) {
      return {
        message: `还有 ${unsplitFileCount} 个 PDF 文件未拆页。建议先生成图纸页。`,
        actions: [
          {
            label: "生成 PDF 图纸页",
            onClick: () => latestBatchId && handleSplitBatch(latestBatchId),
            disabled: !latestBatchId,
            reason: "未找到可处理批次",
            primary: true
          }
        ]
      };
    }
    if (hasDxfWorkPending) {
      return {
        message: "存在未解析 CAD 图纸。建议执行 CAD pipeline。",
        actions: [
          {
            label: "执行 CAD pipeline",
            onClick: () => latestBatchId && handleRunCadPipeline(latestBatchId),
            disabled: !canRunCadPipeline,
            reason: "当前项目暂无 CAD 批次",
            primary: true,
            busy: latestBatchId ? busyAction === `cad-pipeline-${latestBatchId}` : false
          }
        ]
      };
    }
    if (hasCandidatePending) {
      return {
        message: "部分图纸还没有候选值。建议先生成候选值。",
        actions: [
          {
            label: "生成候选值",
            onClick: () => latestBatchId && handleGenerateBatchCandidates(latestBatchId),
            disabled: !latestBatchId || summarySheetCount === 0,
            reason: !latestBatchId ? "未找到可处理批次" : "当前项目暂无图纸",
            primary: true
          }
        ]
      };
    }
    if (summaryMissingDrawingNoCount > 0 || summaryMissingDrawingNameCount > 0) {
      const missingCount = summaryMissingDrawingNoCount > 0 ? summaryMissingDrawingNoCount : summaryMissingDrawingNameCount;
      const missingLabel = summaryMissingDrawingNoCount > 0 ? "图号" : "图名";
      return {
        message: `有 ${missingCount} 张图纸缺少${missingLabel}。建议优先校核缺${missingLabel}图纸。`,
        actions: [
          {
            label: `校核缺${missingLabel}`,
            onClick: () =>
              openReviewFilter({
                missing_field: summaryMissingDrawingNoCount > 0 ? "drawing_no" : "drawing_name"
              }),
            disabled: summarySheetCount === 0,
            reason: "当前项目暂无图纸",
            primary: true
          }
        ]
      };
    }
    if (summaryUnreviewedCount > 0) {
      return {
        message: `还有 ${summaryUnreviewedCount} 张图纸未校核。建议先进入校核工作台完成确认。`,
        actions: [
          {
            label: "进入校核",
            onClick: () => openReviewFilter({ review_status: "unreviewed" }),
            disabled: summarySheetCount === 0,
            reason: "当前项目暂无图纸",
            primary: true
          }
        ]
      };
    }
    return {
      message: "当前项目已基本完成校核，可以导出 Excel 或创建备份。",
      actions: [
        {
          label: "导出 Excel",
          onClick: () => handleExportExcel(true),
          disabled: !canExportProject,
          reason: "当前项目暂无可导出图纸",
          primary: true
        },
        {
          label: "备份项目",
          onClick: handleCreateBackup,
          disabled: backupBusy,
          reason: backupBusy ? "正在备份" : undefined
        }
      ]
    };
  })();
  const projectQuickActions: QuickAction[] = [
    { label: "导入图纸", onClick: () => setImportOpen(true), group: "primary", primary: projectFiles.length === 0 && summarySheetCount === 0 },
    {
      label: "执行 CAD pipeline",
      onClick: () => latestBatchId && handleRunCadPipeline(latestBatchId),
      disabled: !canRunCadPipeline || (latestBatchId ? busyAction === `cad-pipeline-${latestBatchId}` : false),
      reason: !canRunCadPipeline ? "需要先导入 DXF 或 DWG" : busyAction === `cad-pipeline-${latestBatchId}` ? "正在处理" : undefined,
      busy: latestBatchId ? busyAction === `cad-pipeline-${latestBatchId}` : false,
      group: "primary",
      primary: hasDxfWorkPending
    },
    {
      label: "生成 CAD 预览",
      onClick: () => selectedProject && handleGenerateProjectCadPreview(selectedProject.id),
      disabled: !selectedProject || !canGenerateCadPreview || busyAction === `cad-preview-project-${selectedProject?.id}`,
      reason: !canGenerateCadPreview ? "暂无需要预览的 CAD 图纸" : busyAction === `cad-preview-project-${selectedProject?.id}` ? "正在生成" : undefined,
      busy: busyAction === `cad-preview-project-${selectedProject?.id}`,
      group: "primary"
    },
    {
      label: "进入校核工作台",
      onClick: () => openReviewFilter({ review_status: "unreviewed" }),
      disabled: summarySheetCount === 0,
      reason: summarySheetCount === 0 ? "当前项目暂无图纸" : undefined,
      group: "review",
      primary: summaryUnreviewedCount > 0
    },
    {
      label: "导出 Excel",
      onClick: () => handleExportExcel(true),
      disabled: !canExportProject,
      reason: !canExportProject ? "当前项目暂无可导出图纸" : undefined,
      group: "output",
      primary: summarySheetCount > 0 && summaryUnreviewedCount === 0
    },
    {
      label: "备份当前项目",
      onClick: handleCreateBackup,
      disabled: !canBackupProject || backupBusy,
      reason: backupBusy ? "正在备份" : !canBackupProject ? "未打开项目" : undefined,
      busy: backupBusy,
      group: "output"
    },
    {
      label: "运行项目健康检查",
      onClick: handleRunProjectHealthCheck,
      disabled: !selectedProject || maintenanceBusy === "project-health",
      reason: maintenanceBusy === "project-health" ? "正在检查" : !selectedProject ? "未打开项目" : undefined,
      busy: maintenanceBusy === "project-health",
      group: "output"
    }
  ];
  const primaryQuickActions = projectQuickActions.filter((action) => action.group === "primary");
  const reviewQuickActions = projectQuickActions.filter((action) => action.group === "review");
  const outputQuickActions = projectQuickActions.filter((action) => action.group === "output");
  const importItems = importResult?.items ?? [];
  const duplicateImportItems = importItems.filter((item) => item.status === "duplicate" || item.warning === "duplicate_file");
  const unsupportedImportItems = importItems.filter((item) => item.status === "unsupported");
  const failedImportItems = importItems.filter((item) => item.status === "failed");
  const importHasPdf = importResult?.files.some((file) => file.source_format === "pdf") ?? false;
  const importHasDxf = importResult?.files.some((file) => file.source_format === "dxf") ?? false;
  const importHasDwg = importResult?.files.some((file) => file.source_format === "dwg") ?? false;
  const importCanRunCadPipeline = Boolean(importResult && (importHasDxf || (importHasDwg && hasActiveConverter)));
  const importCanGenerateCadPreview = Boolean(importResult && importHasDxf);
  const projectNotice = (() => {
    if (projectFiles.length === 0 && sheetPage.total === 0) {
      return "当前项目还没有导入图纸。";
    }
    if (projectFiles.length > 0 && sheetPage.total === 0 && unsplitFileCount > 0) {
      return "已有 PDF 文件，尚未生成图纸页预览。";
    }
    if (sheets.some((sheet) => sheet.title_crop_status !== "success")) {
      return "部分 PDF 图纸尚未生成标题栏裁剪图。";
    }
    if (sheets.length > 0 && !candidateResult) {
      return "部分图纸尚未生成候选值。可先生成候选值，再进入校核。";
    }
    if (sheets.length > 0 && recommendedCount < sheets.length) {
      return "部分图纸尚未生成推荐字段。可先生成推荐字段，或在校核工作台人工补充。";
    }
    if (issues.some((issue) => issue.status === "open" && issue.severity === "error")) {
      return "当前项目存在阻断问题，确认或导出前建议处理。";
    }
    return "";
  })();

  return (
    <main className="shell">
      <AppHeader health={health} healthError={healthError} />

      <section className="workspace">
        <ProjectsAside
          projects={projects}
          selectedProject={selectedProject}
          loadingProjects={loadingProjects}
          projectError={projectError}
          formError={formError}
          name={name}
          description={description}
          onNameChange={setName}
          onDescriptionChange={setDescription}
          onCreateProject={handleCreateProject}
          onOpenProject={handleOpenProject}
          onDeleteProject={handleDeleteProject}
        />

        <section className="project-home">
          {selectedProject ? (
            <>
              <div className="project-heading">
                <div>
                  <p className="eyebrow">项目首页</p>
                  <h2>{selectedProject.name}</h2>
                  <p>{selectedProject.description || "暂无项目说明。"}</p>
                </div>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => {
                    setEditing((value) => !value);
                    setEditName(selectedProject.name);
                    setEditDescription(selectedProject.description ?? "");
                    setFormError("");
                  }}
                >
                  修改信息
                </button>
              </div>

              {editing ? (
                <form className="edit-form" onSubmit={handleUpdateProject}>
                  <label>
                    项目名称
                    <input
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                    />
                  </label>
                  <label>
                    项目说明
                    <textarea
                      value={editDescription}
                      onChange={(event) => setEditDescription(event.target.value)}
                      rows={3}
                    />
                  </label>
                  {formError ? <p className="form-error">{formError}</p> : null}
                  <div className="inline-actions">
                    <button type="submit">保存修改</button>
                    <button type="button" className="ghost" onClick={() => setEditing(false)}>
                      取消
                    </button>
                  </div>
                </form>
              ) : null}

              <div className="summary-grid project-overview">
                <Metric label="图纸总数" value={summarySheetCount} />
                <Metric label="待校核" value={summaryUnreviewedCount} />
                <Metric label="已确认" value={selectedProject.stats.confirmed_count} />
                <Metric label="问题数量" value={selectedProject.stats.issue_count} />
                <Metric label="已上传文件" value={summaryFileCount} />
              </div>

              <section className="workbench-panel">
                <div className="section-title">
                  <h3>当前项目待办</h3>
                  <span>{workbenchSummary ? "已刷新" : "加载中"}</span>
                </div>
                <div className="todo-groups">
                  <div className="todo-group">
                    <p className="eyebrow">基础</p>
                    <div className="todo-metrics">
                      <TodoMetric label="图纸总数" value={summarySheetCount} onClick={() => applyQuickFilter({})} />
                      <TodoMetric label="图纸文件" value={summaryFileCount} onClick={() => setImportOpen(true)} />
                      <TodoMetric label="已确认" value={selectedProject.stats.confirmed_count} onClick={() => openReviewFilter({ review_status: "confirmed" })} tone="good" />
                      <TodoMetric label="未校核" value={summaryUnreviewedCount} onClick={() => openReviewFilter({ review_status: "unreviewed" })} tone={summaryUnreviewedCount > 0 ? "attention" : "good"} />
                    </div>
                  </div>
                  <div className="todo-group">
                    <p className="eyebrow">质量</p>
                    <div className="todo-metrics">
                      <TodoMetric label="缺图号" value={summaryMissingDrawingNoCount} onClick={() => openReviewFilter({ missing_field: "drawing_no" })} tone={summaryMissingDrawingNoCount > 0 ? "warning" : "good"} />
                      <TodoMetric label="缺图名" value={summaryMissingDrawingNameCount} onClick={() => openReviewFilter({ missing_field: "drawing_name" })} tone={summaryMissingDrawingNameCount > 0 ? "warning" : "good"} />
                      <TodoMetric label="低可信" value={summaryLowConfidenceCount} onClick={() => openReviewFilter({ low_confidence: true })} tone={summaryLowConfidenceCount > 0 ? "attention" : "good"} />
                      <TodoMetric label="error" value={summaryOpenErrorCount} onClick={() => openReviewFilter({ has_error: true })} tone={summaryOpenErrorCount > 0 ? "danger" : "good"} />
                      <TodoMetric label="warning" value={summaryOpenWarningCount} onClick={() => openReviewFilter({ has_warning: true })} tone={summaryOpenWarningCount > 0 ? "warning" : "good"} />
                    </div>
                  </div>
                  <div className="todo-group">
                    <p className="eyebrow">辅助</p>
                    <div className="todo-metrics">
                      <TodoMetric label="CAD 预览缺失" value={summaryCadPreviewMissingCount} onClick={() => applyQuickFilter({ source_format: "dxf" })} tone={summaryCadPreviewMissingCount > 0 ? "attention" : "good"} />
                      <div className="todo-timestamp">
                        <span>最近导入</span>
                        <strong>{workbenchSummary?.last_import_at ? formatDate(workbenchSummary.last_import_at) : "暂无记录"}</strong>
                      </div>
                      <div className="todo-timestamp">
                        <span>最近导出</span>
                        <strong>{workbenchSummary?.last_export_at ? formatDate(workbenchSummary.last_export_at) : "暂无记录"}</strong>
                      </div>
                      <div className="todo-timestamp">
                        <span>最近备份</span>
                        <strong>{workbenchSummary?.last_backup_at ? formatDate(workbenchSummary.last_backup_at) : "暂无记录"}</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              <section className="next-step-panel">
                <div>
                  <p className="eyebrow">下一步建议</p>
                  <h3>{nextStep.message}</h3>
                </div>
                <div className="quick-action-grid">
                  {nextStep.actions.map((action) => (
                    <QuickActionButton action={action} key={action.label} />
                  ))}
                </div>
              </section>

              <section className="quick-workbench">
                <div className="section-title">
                  <h3>快捷操作</h3>
                  <span>常用入口，按当前项目状态推荐</span>
                </div>
                <div className="quick-action-groups">
                  <div>
                    <p className="eyebrow">导入与 CAD</p>
                    <div className="quick-action-grid">
                      {primaryQuickActions.map((action) => (
                        <QuickActionButton action={action} key={action.label} />
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="eyebrow">校核</p>
                    <div className="quick-action-grid">
                      {reviewQuickActions.map((action) => (
                        <QuickActionButton action={action} key={action.label} />
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="eyebrow">交付与维护</p>
                    <div className="quick-action-grid">
                      {outputQuickActions.map((action) => (
                        <QuickActionButton action={action} key={action.label} />
                      ))}
                    </div>
                  </div>
                </div>
              </section>

              <section className="flow-guide">
                <div><strong>PDF 流程</strong><span>上传 PDF → 拆页 → 识别 → 校核 → 导出 Excel</span></div>
                <div><strong>DXF 流程</strong><span>上传 DXF → CAD 解析 → 识别 → CAD 预览 → 校核 → 导出 Excel</span></div>
                <div><strong>DWG 流程</strong><span>上传 DWG → 转 DXF → CAD 解析 → 校核 → 导出 Excel</span></div>
              </section>

              <section className="backup-panel">
                <div className="section-title">
                  <h3>数据安全 / 备份恢复</h3>
                  <span>{backupRecords.length} 个备份</span>
                </div>
                <p className="empty-state">
                  <strong>项目级备份：</strong>项目级备份只备份当前项目，适合迁移或恢复单个项目。
                  <br />
                  <strong>全量备份：</strong>如果要备份全部项目，请关闭系统后复制整个 app_data 目录。
                  <br />
                  <strong>恢复说明：</strong>恢复项目会创建一个新项目，不会覆盖原项目。
                  <br />
                  <strong>升级说明：</strong>升级新版 portable 前，请先备份 app_data；升级后将旧 app_data 复制到新版目录。
                </p>
                <ErrorNotice message={backupError} />
                <div className="inline-actions">
                  <button type="button" onClick={handleCreateBackup} disabled={backupBusy}>
                    {backupBusy ? "正在备份..." : "备份当前项目"}
                  </button>
                </div>
                {backupResult ? (
                  <div className="success-message backup-success">
                    <strong>备份成功</strong>
                    <span>备份文件名：{backupResult.file_name}</span>
                    <span>文件大小：{formatFileSize(backupResult.file_size)}</span>
                    <a className="button-link" href={downloadBackupUrl(backupResult.backup_id)}>
                      下载备份包
                    </a>
                  </div>
                ) : null}
                {restoreBusyId ? <p className="success-message">正在恢复项目...</p> : null}
                {restoreResult ? (
                  <div className="success-message backup-success">
                    <strong>恢复成功，新项目已创建。</strong>
                    <span>新项目名称：{restoreResult.new_project_name}</span>
                    <span>建议下一步：</span>
                    <ol className="compact-steps">
                      <li>打开新项目。</li>
                      <li>检查图纸台账。</li>
                      <li>打开几张图纸详情。</li>
                      <li>导出一次 Excel，确认数据正常。</li>
                    </ol>
                    <div className="inline-actions">
                      <button type="button" onClick={() => handleOpenProject(restoreResult.new_project_id)}>
                        打开新项目
                      </button>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => {
                          setSelectedProject(null);
                          refreshProjects();
                        }}
                      >
                        查看项目列表
                      </button>
                    </div>
                  </div>
                ) : null}
                <div className="sheet-list backup-list">
                  <div className="section-title">
                    <h3>备份列表</h3>
                    <span>{backupRecords.length} 条</span>
                  </div>
                  {backupRecords.length === 0 ? (
                    <EmptyState
                      title="暂无备份记录"
                      description="导出或完成阶段性校核后，建议创建一个项目备份，便于回退或迁移。"
                      actionLabel="备份当前项目"
                      onAction={handleCreateBackup}
                    />
                  ) : (
                    <div className="file-list">
                      {backupRecords.map((record) => (
                        <div className="file-row backup-row" key={record.backup_id}>
                          <span>{formatDate(record.created_at)}</span>
                          <span>{selectedProject.name}</span>
                          <span title={record.file_name}>{record.file_name}</span>
                          <span>{formatFileSize(record.file_size)}</span>
                          <span>{record.status}</span>
                          <span>
                            {verifyResults[record.backup_id]
                              ? verifyResults[record.backup_id].valid
                                ? "校验通过"
                                : "校验异常"
                              : "未校验"}
                          </span>
                          <button
                            type="button"
                            className="ghost"
                            onClick={() => handleVerifyBackup(record.backup_id)}
                            disabled={verifyBusyId === record.backup_id}
                          >
                            {verifyBusyId === record.backup_id ? "校验中..." : "校验备份包"}
                          </button>
                          <a className="text-link" href={downloadBackupUrl(record.backup_id)}>
                            下载
                          </a>
                          <button
                            type="button"
                            onClick={() => handleRestoreBackup(record.backup_id)}
                            disabled={restoreBusyId === record.backup_id || record.status !== "success"}
                          >
                            {restoreBusyId === record.backup_id ? "恢复中..." : "恢复为新项目"}
                          </button>
                          <button
                            type="button"
                            className="ghost"
                            onClick={() => handleDeleteBackup(record.backup_id)}
                            disabled={deleteBackupBusyId === record.backup_id}
                          >
                            {deleteBackupBusyId === record.backup_id ? "删除中..." : "删除"}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  {Object.entries(verifyResults).map(([backupId, result]) => (
                    <div className={result.valid ? "success-message backup-success" : "form-error backup-success"} key={backupId}>
                      <strong>备份 #{backupId} {result.valid ? "校验通过" : "校验异常"}</strong>
                      <span>{backupVerifyMessage(result)}</span>
                      <span>文件数量：{result.summary?.file_count ?? result.counts.manifest_files ?? 0}</span>
                      <span>缺失文件：{result.summary?.missing_file_count ?? result.counts.missing_files ?? 0}</span>
                      <span>checksum 失败：{result.summary?.checksum_failed_count ?? result.counts.checksum_failed ?? 0}</span>
                      {result.warnings.map((warning) => (
                        <span key={warning}>warning：{warning}</span>
                      ))}
                      {result.errors.map((error) => (
                        <span key={error}>error：{error}</span>
                      ))}
                    </div>
                  ))}
                </div>
              </section>

              <section className="maintenance-panel">
                <div className="section-title">
                  <h3>系统维护 / 数据健康检查</h3>
                  <span>只读检查</span>
                </div>
                <p className="empty-state">
                  健康检查会对照数据库记录和 app_data 文件，检查原始图纸、PDF 预览、CAD JSON、CAD 预览、DWG 转换 DXF、Excel 导出和备份包是否存在。本工具不会自动修复数据库，也不会删除项目文件；仅“安全清理临时文件”会清理 app_data/temp。
                </p>
                {dataSafetySummary ? (
                  <div className="summary-grid compact">
                    <Metric label="项目数" value={dataSafetySummary.project_count} />
                    <Metric label="备份记录" value={dataSafetySummary.backup_count} />
                    <Metric label="导出记录" value={dataSafetySummary.export_count} />
                    <Metric label="恢复记录" value={dataSafetySummary.restore_count} />
                    <Metric label="app_data 可写" value={dataSafetySummary.app_data_writable ? 1 : 0} />
                    <Metric label="database 存在" value={dataSafetySummary.database_exists ? 1 : 0} />
                  </div>
                ) : null}
                <ErrorNotice message={maintenanceError} />
                <div className="inline-actions">
                  <button type="button" onClick={handleRunSystemHealthCheck} disabled={maintenanceBusy === "system-health"}>
                    {maintenanceBusy === "system-health" ? "检查中..." : "运行系统健康检查"}
                  </button>
                  <button type="button" onClick={handleRunProjectHealthCheck} disabled={maintenanceBusy === "project-health"}>
                    {maintenanceBusy === "project-health" ? "检查中..." : "检查当前项目"}
                  </button>
                  <button type="button" className="ghost" onClick={handleScanOrphanFiles} disabled={maintenanceBusy === "orphan-scan"}>
                    {maintenanceBusy === "orphan-scan" ? "扫描中..." : "扫描孤儿文件"}
                  </button>
                  <button type="button" className="ghost" onClick={handleBuildMaintenanceReport} disabled={maintenanceBusy === "maintenance-report"}>
                    {maintenanceBusy === "maintenance-report" ? "生成中..." : "生成维护报告"}
                  </button>
                  <button type="button" className="ghost" onClick={handleCleanupTempFiles} disabled={maintenanceBusy === "cleanup-temp"}>
                    {maintenanceBusy === "cleanup-temp" ? "清理中..." : "安全清理 temp"}
                  </button>
                </div>

                {systemHealthResult ? (
                  <div className="health-result">
                    <div className="section-title">
                      <h3>系统健康结果</h3>
                      <span>{dataHealthStatusLabel(systemHealthResult.status)}</span>
                    </div>
                    <div className="summary-grid compact">
                      <Metric label="OK" value={systemHealthResult.summary.ok_count} />
                      <Metric label="Info" value={systemHealthResult.summary.info_count} />
                      <Metric label="Warning" value={systemHealthResult.summary.warning_count} />
                      <Metric label="Error" value={systemHealthResult.summary.error_count} />
                      <Metric label="缺失文件" value={systemHealthResult.summary.missing_file_count} />
                      <Metric label="检查文件" value={systemHealthResult.summary.checked_file_count} />
                      <Metric label="temp 文件" value={systemHealthResult.summary.temp_file_count} />
                    </div>
                    <HealthGroupedSummary grouped={systemHealthResult.grouped_summary} />
                    {healthIssueItems(systemHealthResult.items).length > 0 ? (
                      <HealthIssueList items={systemHealthResult.items} />
                    ) : (
                      <EmptyState
                        title="未发现健康检查问题"
                        description="系统数据目录、导出和备份记录当前没有需要处理的异常。"
                      />
                    )}
                  </div>
                ) : null}

                {projectHealthResult ? (
                  <div className="health-result">
                    <div className="section-title">
                      <h3>当前项目完整性</h3>
                      <span>{dataHealthStatusLabel(projectHealthResult.status)}</span>
                    </div>
                    <div className="summary-grid compact">
                      <Metric label="OK" value={projectHealthResult.summary.ok_count} />
                      <Metric label="Info" value={projectHealthResult.summary.info_count} />
                      <Metric label="Warning" value={projectHealthResult.summary.warning_count} />
                      <Metric label="Error" value={projectHealthResult.summary.error_count} />
                      <Metric label="缺失文件" value={projectHealthResult.summary.missing_file_count} />
                      <Metric label="孤儿文件" value={projectHealthResult.summary.orphan_file_count} />
                      <Metric label="检查文件" value={projectHealthResult.summary.checked_file_count} />
                    </div>
                    <HealthGroupedSummary grouped={projectHealthResult.grouped_summary} />
                    {healthIssueItems(projectHealthResult.items).length > 0 ? (
                      <HealthIssueList items={projectHealthResult.items} />
                    ) : (
                      <EmptyState
                        title="当前项目未发现健康检查问题"
                        description="项目文件、预览、导出和备份引用当前没有需要处理的异常。"
                      />
                    )}
                  </div>
                ) : null}

                {orphanScanResult ? (
                  <div className="health-result">
                    <div className="section-title">
                      <h3>孤儿文件扫描</h3>
                      <span>{orphanScanResult.orphan_files.length} 个</span>
                    </div>
                    {orphanScanResult.orphan_files.length > 0 ? (
                      <div className="file-list health-list">
                        {orphanScanResult.orphan_files.slice(0, 8).map((file) => (
                          <div className="file-row health-row warning" key={file.path}>
                            <span>需关注</span>
                            <span>ORPHAN_FILE</span>
                            <span title={file.path}>{file.path}</span>
                            <span>{formatFileSize(file.size_bytes)}</span>
                            <span>{file.suggestion}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <EmptyState
                        title="未发现孤儿文件"
                        description="项目目录中没有数据库未引用的文件。"
                      />
                    )}
                  </div>
                ) : null}

                {tempCleanupResult ? (
                  <p className={tempCleanupResult.errors.length > 0 ? "form-error" : "success-message"}>
                    temp 清理完成：删除文件 {tempCleanupResult.deleted_file_count} 个，删除空目录 {tempCleanupResult.deleted_dir_count} 个，释放 {formatFileSize(tempCleanupResult.freed_bytes)}。
                    {tempCleanupResult.errors.length > 0 ? ` 错误：${tempCleanupResult.errors.join("；")}` : ""}
                  </p>
                ) : null}
                {maintenanceReportResult ? (
                  <div className="health-result">
                    <div className="section-title">
                      <h3>维护报告</h3>
                      <span>{dataHealthStatusLabel(maintenanceReportResult.status)}</span>
                    </div>
                    <textarea readOnly rows={8} value={maintenanceReportResult.report_markdown} />
                  </div>
                ) : null}
              </section>

              <div className="project-actions">
                <button type="button" onClick={() => setImportOpen((value) => !value)}>
                  导入图纸
                </button>
                <button
                  type="button"
                  disabled={!latestBatchId}
                  onClick={() => latestBatchId && handleSplitBatch(latestBatchId)}
                >
                  生成图纸页预览
                </button>
                <button
                  type="button"
                  disabled={!latestBatchId || preprocessedCount === 0}
                  onClick={() => latestBatchId && handleCropBatchTitles(latestBatchId)}
                >
                  批量生成标题栏裁剪图
                </button>
                <button
                  type="button"
                  disabled={!latestBatchId || sheets.length === 0}
                  onClick={() => latestBatchId && handleExtractBatchText(latestBatchId)}
                >
                  批量提取 PDF 文本
                </button>
                <button
                  type="button"
                  disabled={!latestBatchId || titleCroppedCount === 0}
                  onClick={() => latestBatchId && handleOcrBatchTitles(latestBatchId)}
                >
                  批量识别标题栏 OCR
                </button>
                <button
                  type="button"
                  disabled={!latestBatchId || sheets.length === 0}
                  onClick={() => latestBatchId && handleGenerateBatchCandidates(latestBatchId)}
                >
                  批量生成候选值
                </button>
                <button
                  type="button"
                  disabled={!latestBatchId || sheets.length === 0}
                  onClick={() => latestBatchId && handleFuseBatchFields(latestBatchId)}
                >
                  批量生成推荐字段
                </button>
                <button type="button" disabled={sheets.length === 0} onClick={() => handleBatchConfirm("trust_a")}>
                  批量确认 A 级图纸
                </button>
                <button type="button" disabled>
                  继续校核：暂无待校核图纸
                </button>
                <button type="button" disabled>
                  导出 Excel：暂无可导出数据
                </button>
              </div>

              <section className="pipeline-panel">
                <div className="section-title">
                  <h3>CAD 批量处理</h3>
                  <span>{latestBatchId ? `批次 #${latestBatchId}` : "等待导入批次"}</span>
                </div>
                <p className="empty-state">
                  该功能用于批量处理 DWG / DXF 文件。系统不会直接解析 DWG，而是先调用已配置的外部工具转换为 DXF。转换成功后，将继续执行 DXF 解析、候选值生成和推荐字段生成。
                </p>
                <div className="summary-grid compact">
                  <Metric label="PDF 文件" value={pdfFileCount} />
                  <Metric label="DWG 文件" value={dwgFileCount} />
                  <Metric label="DXF 文件" value={dxfFileCount} />
                  <Metric label="已转换 DWG" value={convertedDwgCount} />
                  <Metric label="待转换 DWG" value={pendingDwgFiles.length} />
                  <Metric label="已创建 sheet" value={dxfSheetCount} />
                  <Metric label="已解析 DXF" value={dxfParsedCount} />
                  <Metric label="已生成候选值" value={cadPipelineResult?.summary.candidate_success ?? 0} />
                  <Metric label="CAD 预览" value={cadPipelineResult?.summary.cad_preview_success ?? 0} />
                  <Metric label="推荐字段" value={dxfRecommendedCount} />
                  <Metric label="失败数量" value={failedSheetCount + pendingDwgFiles.filter((file) => file.convert_status === "failed").length} />
                </div>
                <div className="pipeline-options">
                  {([
                    "convert_dwg",
                    "prepare_dxf_sheet",
                    "parse_dxf",
                    "generate_candidates",
                    "fuse_fields",
                    "generate_cad_preview"
                  ] as CadPipelineStep[]).map((step) => (
                    <label key={step}>
                      <input
                        type="checkbox"
                        checked={cadPipelineSteps.includes(step)}
                        onChange={() => toggleCadPipelineStep(step)}
                      />
                      {pipelineStepLabel(step)}
                    </label>
                  ))}
                </div>
                <div className="pipeline-options">
                  <label>
                    <input
                      type="checkbox"
                      checked={cadPipelineSkipCompleted}
                      onChange={(event) => setCadPipelineSkipCompleted(event.target.checked)}
                    />
                    跳过已完成步骤
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={cadPipelineContinueOnError}
                      onChange={(event) => setCadPipelineContinueOnError(event.target.checked)}
                    />
                    单个失败继续处理
                  </label>
                </div>
                <div className="pipeline-options">
                  <label>
                    <input
                      type="checkbox"
                      checked={cadPreviewSkipCompleted}
                      onChange={(event) => setCadPreviewSkipCompleted(event.target.checked)}
                    />
                    批量预览跳过已生成
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={cadPreviewForce}
                      onChange={(event) => setCadPreviewForce(event.target.checked)}
                    />
                    强制重新生成预览
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={cadPreviewContinueOnError}
                      onChange={(event) => setCadPreviewContinueOnError(event.target.checked)}
                    />
                    单张失败继续生成
                  </label>
                </div>
                <button
                  type="button"
                  disabled={!latestBatchId || busyAction === `cad-pipeline-${latestBatchId}`}
                  onClick={() => latestBatchId && handleRunCadPipeline(latestBatchId)}
                >
                  {latestBatchId && busyAction === `cad-pipeline-${latestBatchId}` ? "批量处理中..." : "开始批量处理"}
                </button>
                <button
                  type="button"
                  disabled={!latestBatchId || busyAction === `cad-preview-batch-${latestBatchId}`}
                  onClick={() => latestBatchId && handleGenerateBatchCadPreview(latestBatchId)}
                >
                  {latestBatchId && busyAction === `cad-preview-batch-${latestBatchId}` ? "正在生成 CAD 预览..." : "开始批量生成预览"}
                </button>
                <button
                  type="button"
                  disabled={!selectedProject || busyAction === `cad-preview-project-${selectedProject?.id}`}
                  onClick={() => selectedProject && handleGenerateProjectCadPreview(selectedProject.id)}
                >
                  {selectedProject && busyAction === `cad-preview-project-${selectedProject.id}` ? "正在生成项目预览..." : "项目级批量生成 CAD 预览"}
                </button>
                {cadPipelineJob && cadPipelineJob.status === "running" ? (
                  <div className="pipeline-running">
                    <strong>正在批量处理，请勿关闭页面</strong>
                    <span>
                      步骤 {cadPipelineJob.processed}/{cadPipelineJob.total}
                      {cadPipelineJob.current_step
                        ? `：${pipelineStepLabel(cadPipelineJob.current_step as CadPipelineStep)}`
                        : ""}
                    </span>
                    <div
                      style={{
                        background: "rgba(0,0,0,0.06)",
                        borderRadius: 999,
                        height: 6,
                        overflow: "hidden",
                        margin: "8px 0"
                      }}
                    >
                      <div
                        style={{
                          width: `${cadPipelineJob.total ? (cadPipelineJob.processed / cadPipelineJob.total) * 100 : 0}%`,
                          height: "100%",
                          background: "#7ea4ff",
                          transition: "width 200ms ease"
                        }}
                      />
                    </div>
                    <span>耗时：{formatDuration(cadPipelineElapsed)}</span>
                  </div>
                ) : null}
                <ErrorNotice message={cadPipelineError} />
                {latestBatchId && busyAction === `cad-preview-batch-${latestBatchId}` ? (
                  <div className="pipeline-running">
                    <strong>正在生成 CAD 预览...</strong>
                    <span>选项：{cadPreviewSkipCompleted ? "跳过已生成" : "不跳过"}，{cadPreviewForce ? "强制刷新" : "保留缓存"}，{cadPreviewContinueOnError ? "失败继续" : "遇错停止"}</span>
                    <span>完成后会显示成功、失败、跳过和耗时统计。</span>
                  </div>
                ) : null}
                {selectedProject && busyAction === `cad-preview-project-${selectedProject.id}` ? (
                  <div className="pipeline-running">
                    <strong>正在生成项目 CAD 预览...</strong>
                    <span>项目范围会处理所有 DXF 和已转换 DWG 图纸页。</span>
                  </div>
                ) : null}
                {cadPipelineResult ? (
                  <div className="pipeline-result">
                    <p className="success-message">
                      流水线状态：{pipelineStatusLabel(cadPipelineResult.status)}。总耗时 {formatDuration(cadPipelineResult.summary.duration_seconds)}，成功 {pipelineSuccessTotal(cadPipelineResult)} 项，失败 {pipelineFailureTotal(cadPipelineResult)} 项，跳过 {cadPipelineResult.summary.skipped_count} 项。
                    </p>
                    <p className="empty-state">{pipelineNextSuggestion(cadPipelineResult)}</p>
                    <div className="file-list">
                      {cadPipelineResult.steps.map((step) => (
                        <div className="file-row" key={step.step}>
                          <span>{pipelineStepLabel(step.step)}</span>
                          <span>{pipelineStatusLabel(step.status)}</span>
                          <span>成功 {step.success_count}</span>
                          <span>失败 {step.failed_count}</span>
                          <span>跳过 {step.skipped_count}</span>
                          <span>耗时 {formatDuration(step.duration_seconds)}</span>
                        </div>
                      ))}
                    </div>
                    {cadPipelineResult.errors.length > 0 ? (
                      <div className="file-list">
                        {cadPipelineResult.errors.map((error, index) => (
                          <div className="file-row" key={`${error.step}-${error.file_id ?? "batch"}-${index}`}>
                            <span>{error.file_name || (error.file_id ? `文件 #${error.file_id}` : "批次")}</span>
                            <span>{pipelineStepLabel(error.step)}</span>
                            <span>{error.error_code}</span>
                            <span>{error.message}</span>
                            <span>{pipelineErrorSuggestion(error.error_code)}</span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                {batchCadPreviewResult ? (
                  <div className="pipeline-result">
                    <p className={batchCadPreviewResult.failed_count > 0 ? "form-error" : "success-message"}>
                      CAD 预览批量生成完成：状态 {pipelineStatusLabel(batchCadPreviewResult.status)}，
                      总数 {batchCadPreviewResult.summary.total_count}，成功 {batchCadPreviewResult.summary.success_count}，
                      失败 {batchCadPreviewResult.summary.failed_count}，跳过 {batchCadPreviewResult.summary.skipped_count}，
                      warning {batchCadPreviewResult.summary.warning_count}，耗时 {formatDuration(batchCadPreviewResult.summary.duration_seconds)}。
                    </p>
                    {batchCadPreviewResult.warnings.length > 0 ? (
                      <p className="empty-state">{batchCadPreviewResult.warnings.join("；")}</p>
                    ) : null}
                    {batchCadPreviewResult.errors.length > 0 ? (
                      <div className="file-list">
                        {batchCadPreviewResult.errors.map((error, index) => (
                          <div className="file-row" key={`${error.sheet_id ?? "sheet"}-${index}`}>
                            <span>{error.file_name || (error.sheet_id ? `sheet #${error.sheet_id}` : "CAD 图纸")}</span>
                            <span>{error.error_code}</span>
                            <span>{error.message}</span>
                            <span>{pipelineErrorSuggestion(error.error_code)}</span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </section>

              {projectFiles.length > 0 ? (
                <div className="recent-files">
                  <h3>最近导入</h3>
                  <p>
                    已上传 {projectFiles.length} 个图纸文件（PDF {pdfFileCount} 个，DXF {dxfFileCount} 个，DWG {dwgFileCount} 个），最近导入时间：
                    {formatDate(projectFiles[0]?.created_at ?? null)}
                  </p>
                  {unsplitFileCount > 0 ? (
                    <p>有 {unsplitFileCount} 个 PDF 文件尚未拆页。</p>
                  ) : null}
                  {pendingDxfFiles.length > 0 ? (
                    <p>有 {pendingDxfFiles.length} 个 DXF 文件已上传，尚未创建图纸页。</p>
                  ) : null}
                  {pendingDwgFiles.length > 0 ? (
                    <p>有 {pendingDwgFiles.length} 个 DWG 文件已上传，尚未转换为 DXF。</p>
                  ) : null}
                  <div className="file-list">
                    {projectFiles.slice(0, 5).map((file) => (
                      <div className="file-row" key={file.id}>
                        <span>{file.original_name}</span>
                        <span>{file.source_format.toUpperCase()}</span>
                        <span>{formatFileSize(file.file_size)}</span>
                        <span>
                          {file.source_format === "dxf" && file.status === "cad_parsed"
                            ? "DXF 已解析。"
                            : file.source_format === "dwg" && file.convert_status === "success"
                              ? "DWG 已转换为 DXF，可继续执行 DXF 解析。"
                            : file.source_format === "dwg" && file.convert_status === "failed"
                              ? `DWG 转换失败：${file.convert_error_code || ""}`
                            : file.source_format === "dwg"
                              ? "DWG 已上传，尚未转换为 DXF。"
                            : file.source_format === "dxf" && ["recognized", "need_review", "confirmed"].includes(file.status)
                              ? "推荐字段已生成。"
                            : file.source_format === "dxf" && file.status === "cad_pending"
                              ? "DXF 图纸页已创建，尚未解析 DXF 实体。"
                            : file.source_format === "dxf"
                              ? "DXF 文件已上传，尚未创建图纸页。"
                              : statusLabel(file.status)}
                        </span>
                        {file.source_format === "dxf" && file.status === "imported" ? (
                          <button type="button" disabled={busyAction === `prepare-${file.id}`} onClick={() => handlePrepareDxfSheet(file.id)}>
                            {busyAction === `prepare-${file.id}` ? "准备中..." : "准备 DXF 图纸页"}
                          </button>
                        ) : null}
                        {file.source_format === "dwg" && file.convert_status !== "success" ? (
                          <button type="button" disabled={busyAction === `convert-${file.id}`} onClick={() => handleConvertDwgFile(file.id)}>
                            {busyAction === `convert-${file.id}` ? "转换中..." : "转换为 DXF"}
                          </button>
                        ) : null}
                        {file.source_format === "dwg" && file.convert_status === "success" && file.status === "imported" ? (
                          <button type="button" disabled={busyAction === `prepare-${file.id}`} onClick={() => handlePrepareDxfSheet(file.id)}>
                            {busyAction === `prepare-${file.id}` ? "准备中..." : "准备 DXF 图纸页"}
                          </button>
                        ) : null}
                        {file.source_format === "dwg" && file.convert_status === "success" && file.status !== "imported" ? (
                          <button type="button" disabled={busyAction === `parse-${file.id}`} onClick={() => handleParseDxfFile(file.id)}>
                            {busyAction === `parse-${file.id}` ? "解析中..." : "解析 DXF"}
                          </button>
                        ) : null}
                        {file.source_format === "dxf" && file.status !== "imported" ? (
                          <button type="button" disabled={busyAction === `parse-${file.id}`} onClick={() => handleParseDxfFile(file.id)}>
                            {busyAction === `parse-${file.id}` ? "解析中..." : "解析 DXF"}
                          </button>
                        ) : null}
                        {isCadReadyFile(file) && sheetByFileId.get(file.id) ? (
                          <button type="button" onClick={() => handleLoadCadParseSummary(sheetByFileId.get(file.id)!.id)}>
                            查看 CAD 解析摘要
                          </button>
                        ) : null}
                        {isCadReadyFile(file) && sheetByFileId.get(file.id) ? (
                          <button
                            type="button"
                            disabled={busyAction === `cad-preview-${sheetByFileId.get(file.id)!.id}`}
                            onClick={() => handleGenerateCadPreview(sheetByFileId.get(file.id)!.id)}
                          >
                            {busyAction === `cad-preview-${sheetByFileId.get(file.id)!.id}` ? "生成预览中..." : "生成 CAD 预览"}
                          </button>
                        ) : null}
                        {isCadReadyFile(file) && sheetByFileId.get(file.id) ? (
                          <button type="button" onClick={() => handleGenerateSheetCandidates(sheetByFileId.get(file.id)!.id)}>
                            生成候选值
                          </button>
                        ) : null}
                        {isCadReadyFile(file) && sheetByFileId.get(file.id) ? (
                          <button type="button" onClick={() => handleFuseSheetFields(sheetByFileId.get(file.id)!.id)}>
                            生成推荐字段
                          </button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                  {pendingDxfFiles.length > 0 && latestBatchId ? (
                    <button type="button" disabled={busyAction === `prepare-batch-${latestBatchId}`} onClick={() => handlePrepareBatchDxfSheets(latestBatchId)}>
                      {busyAction === `prepare-batch-${latestBatchId}` ? "批量准备中..." : "批量准备 DXF 图纸页"}
                    </button>
                  ) : null}
                  {dxfFileCount + convertedDwgCount > 0 && latestBatchId ? (
                    <button type="button" disabled={busyAction === `parse-batch-${latestBatchId}`} onClick={() => handleParseDxfBatch(latestBatchId)}>
                      {busyAction === `parse-batch-${latestBatchId}` ? "批量解析中..." : "批量解析 DXF"}
                    </button>
                  ) : null}
                  {dxfFileCount + convertedDwgCount > 0 && latestBatchId ? (
                    <button type="button" disabled={busyAction === `cad-preview-batch-${latestBatchId}`} onClick={() => handleGenerateBatchCadPreview(latestBatchId)}>
                      {busyAction === `cad-preview-batch-${latestBatchId}` ? "批量生成预览中..." : "批量生成 CAD 预览"}
                    </button>
                  ) : null}
                  {pendingDwgFiles.length > 0 && latestBatchId ? (
                    <button type="button" disabled={busyAction === `convert-batch-${latestBatchId}`} onClick={() => handleConvertDwgBatch(latestBatchId)}>
                      {busyAction === `convert-batch-${latestBatchId}` ? "批量转换中..." : "批量转换 DWG"}
                    </button>
                  ) : null}
                </div>
              ) : null}

              <section className="converter-panel">
                <div className="section-title">
                  <h3>CAD 转换设置</h3>
                  <span>DWG 转 DXF</span>
                </div>
                <p className="empty-state">
                  当前系统不直接解析 DWG。如需处理 DWG，请先配置本机 DWG 转 DXF 工具。当前不会内置 DWG 转换工具，请自行安装 ODA File Converter 或其他可命令行转换 DWG 到 DXF 的工具，并在设置中配置路径。
                </p>
                <form className="converter-form" onSubmit={handleSaveConverterSettings}>
                  <label>
                    转换工具名称
                    <input value={converterName} onChange={(event) => setConverterName(event.target.value)} />
                  </label>
                  <label>
                    exe 路径
                    <input value={converterExePath} onChange={(event) => setConverterExePath(event.target.value)} placeholder="C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe" />
                  </label>
                  <label>
                    输出版本
                    <input value={converterOutputVersion} onChange={(event) => setConverterOutputVersion(event.target.value)} />
                  </label>
                  <div className="inline-actions">
                    <button type="submit">保存配置</button>
                    <button type="button" onClick={handleCheckConverter} disabled={busyAction.startsWith("check-converter")}>
                      {busyAction.startsWith("check-converter") ? "检测中..." : "检测工具"}
                    </button>
                  </div>
                </form>
                {converterMessage ? <p className="success-message">{converterMessage}</p> : null}
                <ErrorNotice message={converterError} />
                {dwgConvertResult?.status === "success" ? (
                  <p className="success-message">DWG 已转换为 DXF：{dwgConvertResult.converted_file_path}</p>
                ) : null}
                {batchDwgConvertResult ? (
                  <div className="conversion-summary">
                    <p className="success-message">
                      批量转换完成：总数 {batchDwgConvertResult.total_count} 个，成功 {batchDwgConvertResult.success_count} 个，失败 {batchDwgConvertResult.failed_count} 个，跳过 {batchDwgConvertResult.skipped_count} 个。
                    </p>
                    {batchDwgConvertResult.items.some((item) => item.status === "failed") ? (
                      <div className="file-list">
                        {batchDwgConvertResult.items
                          .filter((item) => item.status === "failed")
                          .map((item) => (
                            <div className="file-row" key={item.file_id}>
                              <span>文件 #{item.file_id}</span>
                              <span>转换失败</span>
                              <span>{item.error_code || "-"}</span>
                              <span>{item.error_message || "-"}</span>
                            </div>
                          ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                {conversionRuns.length > 0 ? (
                  <div className="file-list">
                    {conversionRuns.slice(0, 5).map((run) => (
                      <div className="file-row run-row" key={run.id}>
                        <span>{formatDate(run.finished_at)}</span>
                        <span>{run.converter_name}</span>
                        <span>{run.status}</span>
                        <span>{run.error_code || run.target_path || "-"}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </section>

              {importOpen ? (
                <form className="import-panel" onSubmit={handleUpload}>
                  <div className="section-title">
                    <h3>导入图纸文件</h3>
                    <span>PDF / DXF / DWG</span>
                  </div>
                  <div className="import-guide">
                    <strong>支持格式</strong>
                    <div className="import-guide-grid">
                      <span>PDF 会先拆页，再识别标题栏信息。</span>
                      <span>DXF 可直接进入 CAD 解析流程。</span>
                      <span>DWG 需要通过外部工具转换为 DXF 后识别。</span>
                      <span>不支持图片、Word、Excel、压缩包等直接导入为图纸。</span>
                    </div>
                  </div>
                  <label>
                    批次名称
                    <input
                      value={batchName}
                      onChange={(event) => setBatchName(event.target.value)}
                      placeholder="例如：第一次导入"
                    />
                  </label>
                  <label>
                    备注
                    <textarea
                      value={remark}
                      onChange={(event) => setRemark(event.target.value)}
                      rows={3}
                      placeholder="可选"
                    />
                  </label>
                  <label>
                    图纸文件
                    <input
                      type="file"
                      accept="application/pdf,.pdf,.dxf,.dwg"
                      multiple
                      onChange={handleSelectFiles}
                    />
                  </label>
                  {selectedFiles.length > 0 || selectedRejectedFiles.length > 0 ? (
                    <div className="import-precheck">
                      <div className="section-title">
                        <h3>文件预检查</h3>
                        <span>本次选择 {selectedFiles.length + selectedRejectedFiles.length} 个文件，合计 {formatFileSize(selectedTotalSize)}</span>
                      </div>
                      <div className="summary-grid compact import-summary-grid">
                        <Metric label="PDF" value={selectedFileTypeCounts.pdf} />
                        <Metric label="DXF" value={selectedFileTypeCounts.dxf} />
                        <Metric label="DWG" value={selectedFileTypeCounts.dwg} />
                        <Metric label="不支持" value={selectedFileTypeCounts.unsupported} />
                        <Metric label="重名提示" value={selectedDuplicateNames.length + existingDuplicateNames.length} />
                        <Metric label="超大文件" value={selectedOversizedFiles.length} />
                      </div>
                      {selectedFiles.length > 0 ? (
                        <div className="file-list">
                          {selectedFiles.map((file) => (
                            <div className="file-row import-file-row" key={`${file.name}-${file.size}`}>
                              <span>{file.name}</span>
                              <span>{formatFileSize(file.size)}</span>
                              <span>{drawingFileLabel(file.name)}</span>
                              <span>{file.size > UPLOAD_MAX_BYTES ? "超过大小限制" : "可导入"}</span>
                            </div>
                          ))}
                        </div>
                      ) : null}
                      {selectedRejectedFiles.length > 0 ? (
                        <div className="import-warning">
                          <strong>以下文件格式暂不支持，请移除后继续。</strong>
                          {selectedRejectedFiles.map((file) => (
                            <span key={`${file.name}-${file.size}`}>{file.name}：{file.reason}</span>
                          ))}
                        </div>
                      ) : null}
                      {selectedOversizedFiles.length > 0 ? (
                        <div className="import-warning">
                          <strong>以下文件超过大小限制，请移除后继续。</strong>
                          {selectedOversizedFiles.map((file) => (
                            <span key={`${file.name}-${file.size}`}>{file.name}：{formatFileSize(file.size)}，上限 {formatFileSize(UPLOAD_MAX_BYTES)}</span>
                          ))}
                        </div>
                      ) : null}
                      {selectedDuplicateNames.length > 0 || existingDuplicateNames.length > 0 ? (
                        <div className="import-note">
                          {selectedDuplicateNames.length > 0 ? (
                            <span>本次选择中有重名文件：{selectedDuplicateNames.join("、")}。</span>
                          ) : null}
                          {existingDuplicateNames.length > 0 ? (
                            <span>项目中已有同名文件：{existingDuplicateNames.join("、")}，后端仍会按文件内容判断是否重复。</span>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <EmptyState
                      title="还没有选择图纸文件"
                      description="请选择一个或多个 PDF、DXF 或 DWG 文件，系统会按文件类型进入对应流程。"
                    />
                  )}
                  <ErrorNotice message={importError} />
                  <button type="submit" disabled={selectedRejectedFiles.length > 0 || selectedOversizedFiles.length > 0}>
                    开始导入
                  </button>
                </form>
              ) : null}

              {importResult ? (
                <div className="import-result">
                  <div className="section-title">
                    <h3>导入结果</h3>
                    <span>本次选择 {importResult.total_selected} 个文件</span>
                  </div>
                  <p>批次名称：{importResult.batch_name}</p>
                  <div className="summary-grid compact import-summary-grid">
                    <Metric label="选择文件" value={importResult.total_selected} />
                    <Metric label="成功导入" value={importResult.imported_count} />
                    <Metric label="PDF" value={importResult.file_type_counts.pdf ?? 0} />
                    <Metric label="DXF" value={importResult.file_type_counts.dxf ?? 0} />
                    <Metric label="DWG" value={importResult.file_type_counts.dwg ?? 0} />
                    <Metric label="重复文件" value={importResult.duplicate_count} />
                    <Metric label="不支持格式" value={importResult.unsupported_count} />
                    <Metric label="失败数量" value={importResult.failed_count} />
                  </div>
                  {importItems.length > 0 ? (
                    <div className="file-list import-items-list">
                      {importItems.map((item, index) => (
                        <div className={`file-row import-item-row ${item.status}`} key={`${item.file_name}-${item.status}-${index}`}>
                          <span>{item.file_name}</span>
                          <span>{drawingKindLabel(item.file_type)}</span>
                          <span>{importItemStatusLabel(item.status)}</span>
                          <span>{item.error_code || item.warning || "-"}</span>
                          <span>{item.message || (item.status === "imported" ? "已导入，可继续下一步。" : "-")}</span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {duplicateImportItems.length > 0 ? (
                    <div className="import-note">
                      <strong>以下文件疑似已导入过，本次已跳过或标记为重复：</strong>
                      {duplicateImportItems.map((item) => (
                        <span key={`${item.file_name}-${item.status}`}>{item.file_name}</span>
                      ))}
                    </div>
                  ) : null}
                  {unsupportedImportItems.length > 0 ? (
                    <div className="import-warning">
                      <strong>不支持格式</strong>
                      {unsupportedImportItems.map((item) => (
                        <span key={`${item.file_name}-${item.error_code}`}>{item.file_name}：{item.message || "当前文件格式不支持。"}</span>
                      ))}
                    </div>
                  ) : null}
                  {failedImportItems.length > 0 ? (
                    <div className="import-warning">
                      <strong>导入失败</strong>
                      {failedImportItems.map((item) => (
                        <span key={`${item.file_name}-${item.error_code}`}>{item.file_name}：错误码 {item.error_code || "-"}，说明 {item.message || "-"}</span>
                      ))}
                    </div>
                  ) : null}
                  <div className="import-next-step">
                    <strong>{importNextSuggestion(importResult, hasActiveConverter)}</strong>
                    <div className="inline-actions">
                      {importHasPdf ? (
                        <button type="button" onClick={() => handleSplitBatch(importResult.id)}>
                          生成 PDF 图纸页
                        </button>
                      ) : null}
                      {importHasDwg && !hasActiveConverter ? (
                        <button type="button" className="primary-button" onClick={scrollToConverterSettings}>
                          配置转换工具
                        </button>
                      ) : null}
                      {importHasDwg && !hasActiveConverter ? (
                        <button type="button" onClick={scrollToConverterSettings}>
                          查看 DWG 使用说明
                        </button>
                      ) : null}
                      {importHasDwg && hasActiveConverter ? (
                        <button type="button" onClick={() => handleConvertDwgBatch(importResult.id)}>
                          执行 DWG 转 DXF
                        </button>
                      ) : null}
                      {importCanRunCadPipeline ? (
                        <button
                          type="button"
                          disabled={busyAction === `cad-pipeline-${importResult.id}`}
                          onClick={() => handleRunCadPipeline(importResult.id)}
                        >
                          {busyAction === `cad-pipeline-${importResult.id}` ? "处理中..." : "执行 CAD pipeline"}
                        </button>
                      ) : null}
                      {importCanGenerateCadPreview ? (
                        <button
                          type="button"
                          disabled={busyAction === `cad-preview-batch-${importResult.id}`}
                          onClick={() => handleGenerateBatchCadPreview(importResult.id)}
                        >
                          {busyAction === `cad-preview-batch-${importResult.id}` ? "生成中..." : "生成 CAD 预览"}
                        </button>
                      ) : null}
                      <button type="button" onClick={returnToProjectHome}>
                        返回项目首页
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}

              <ErrorNotice message={splitError} />
              <ErrorNotice message={dxfPrepareError} />
              <ErrorNotice message={cadParseError} />
              <ErrorNotice message={cadPreviewError} />
              <ErrorNotice message={titleCropError} />
              <ErrorNotice message={recognitionError} />
              <ErrorNotice message={candidateError} />
              <ErrorNotice message={fusionError} />

              {cadPreviewResult ? (
                <p className={cadPreviewResult.status === "success" ? "success-message" : "form-error"}>
                  CAD 预览{cadPreviewResult.status === "success" ? "生成成功" : "生成失败"}：
                  {cadPreviewResult.error_code || cadPreviewResult.cad_preview_path || "-"}。
                  耗时 {formatDuration(cadPreviewResult.duration_seconds)}，跳过实体 {cadPreviewResult.skipped_entity_count} 个。
                  {cadPreviewResult.warnings.length > 0 ? ` warning：${cadPreviewResult.warnings.join("；")}` : ""}
                </p>
              ) : null}
              {batchCadPreviewResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>CAD 预览批量结果</h3>
                    <span>{pipelineStatusLabel(batchCadPreviewResult.status)}</span>
                  </div>
                  <p>
                    总数 {batchCadPreviewResult.summary.total_count}，成功 {batchCadPreviewResult.summary.success_count}，
                    失败 {batchCadPreviewResult.summary.failed_count}，跳过 {batchCadPreviewResult.summary.skipped_count}，
                    warning {batchCadPreviewResult.summary.warning_count}，耗时 {formatDuration(batchCadPreviewResult.summary.duration_seconds)}。
                  </p>
                </div>
              ) : null}

              {splitResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>拆页结果</h3>
                    <span>{splitResult.sheet_count} 页</span>
                  </div>
                  <p>
                    文件数量：{splitResult.file_count}，成功页数：
                    {splitResult.sheet_count - splitResult.failed_count}，失败页数：
                    {splitResult.failed_count}
                  </p>
                </div>
              ) : null}

              {dxfPrepareResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>DXF 图纸页准备结果</h3>
                    <span>{dxfPrepareResult.created ? "已创建" : "已存在"}</span>
                  </div>
                  <p>DXF 图纸页已创建，尚未解析 DXF 实体。</p>
                </div>
              ) : null}

              {batchDxfPrepareResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>批量 DXF 图纸页准备结果</h3>
                    <span>{batchDxfPrepareResult.total_dxf_count} 个 DXF</span>
                  </div>
                  <p>
                    新建：{batchDxfPrepareResult.created_count}，已存在：
                    {batchDxfPrepareResult.existing_count}，失败：
                    {batchDxfPrepareResult.failed_count}
                  </p>
                  {batchDxfPrepareResult.items.some((item) => item.error_code) ? (
                    <div className="file-list">
                      {batchDxfPrepareResult.items
                        .filter((item) => item.error_code)
                        .map((item) => (
                          <div className="file-row" key={item.file_id}>
                            <span>File {item.file_id}</span>
                            <span>{item.error_code}</span>
                            <span>{item.message || "-"}</span>
                          </div>
                        ))}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {cadParseResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>DXF 解析结果</h3>
                    <span>{cadParseResult.status}</span>
                  </div>
                  <p>
                    TEXT：{cadParseResult.counts.text_count ?? 0}，MTEXT：
                    {cadParseResult.counts.mtext_count ?? 0}，INSERT：
                    {cadParseResult.counts.insert_count ?? 0}，ATTRIB：
                    {cadParseResult.counts.attrib_count ?? 0}，图层：
                    {cadParseResult.counts.layer_count ?? 0}
                  </p>
                  {cadParseResult.warnings.length > 0 ? (
                    <p className="empty-state">Warnings：{cadParseResult.warnings.join(", ")}</p>
                  ) : null}
                </div>
              ) : null}

              {batchCadParseResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>批量 DXF 解析结果</h3>
                    <span>{batchCadParseResult.total_count} 个 DXF</span>
                  </div>
                  <p>
                    成功：{batchCadParseResult.success_count}，失败：
                    {batchCadParseResult.failed_count}，跳过：
                    {batchCadParseResult.skipped_count}
                  </p>
                  {batchCadParseResult.items.some((item) => item.status === "failed") ? (
                    <div className="file-list">
                      {batchCadParseResult.items
                        .filter((item) => item.status === "failed")
                        .map((item) => (
                          <div className="file-row" key={item.file_id}>
                            <span>File {item.file_id}</span>
                            <span>{item.error_code || "-"}</span>
                            <span>{item.error_message || "-"}</span>
                          </div>
                        ))}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {titleCropResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>标题栏裁剪结果</h3>
                    <span>{titleCropResult.total_count} 页</span>
                  </div>
                  <p>
                    成功数量：{titleCropResult.success_count}，失败数量：
                    {titleCropResult.failed_count}
                  </p>
                </div>
              ) : null}

              {recognitionResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>文本提取 / OCR 结果</h3>
                    <span>{recognitionResult.total_count} 项</span>
                  </div>
                  <p className="empty-state">当前 OCR 为内测占位能力，扫描 PDF 识别质量有限。</p>
                  <p>
                    成功数量：{recognitionResult.success_count}，失败数量：
                    {recognitionResult.failed_count}
                  </p>
                  <div className="file-list">
                    {recognitionResult.items.slice(0, 5).map((item) => (
                      <div className="file-row" key={`${item.sheet_id}-${item.run_type}`}>
                        <span>
                          Sheet {item.sheet_id} {item.run_type}
                        </span>
                        <span>{item.status}</span>
                        <span>{item.text_length} 字</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {ocrJob ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>批量标题栏 OCR</h3>
                    <span>
                      {ocrJob.processed}/{ocrJob.total}
                      {ocrJob.status === "running" ? " 处理中" : ocrJob.status === "completed" ? " 完成" : ocrJob.status === "failed" ? " 失败" : ""}
                    </span>
                  </div>
                  <div
                    style={{
                      background: "rgba(0,0,0,0.06)",
                      borderRadius: 999,
                      height: 6,
                      overflow: "hidden",
                      margin: "8px 0"
                    }}
                  >
                    <div
                      style={{
                        width: `${ocrJob.total ? (ocrJob.processed / ocrJob.total) * 100 : 0}%`,
                        height: "100%",
                        background:
                          ocrJob.status === "failed"
                            ? "#f5a4a4"
                            : ocrJob.status === "completed"
                            ? "#7ec8a8"
                            : "#7ea4ff",
                        transition: "width 200ms ease"
                      }}
                    />
                  </div>
                  <p>
                    成功 {ocrJob.success_count}，失败 {ocrJob.failed_count}
                    {ocrJob.message ? `（${ocrJob.message}）` : ""}
                  </p>
                </div>
              ) : null}

              {candidateResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>候选值生成结果</h3>
                    <span>{candidateResult.candidate_count} 个候选</span>
                  </div>
                  <p>
                    图纸页数量：{candidateResult.total_count}，成功：
                    {candidateResult.success_count}，失败：{candidateResult.failed_count}
                  </p>
                </div>
              ) : null}

              {fusionResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>推荐字段生成结果</h3>
                    <span>{fusionResult.issue_count} 个问题</span>
                  </div>
                  <p>
                    图纸页数量：{fusionResult.total_count}，成功：
                    {fusionResult.success_count}，失败：{fusionResult.failed_count}
                  </p>
                </div>
              ) : null}

              {batchConfirmResult ? (
                <div className="split-result">
                  <div className="section-title">
                    <h3>批量确认结果</h3>
                    <span>{batchConfirmResult.confirmed_count} 张已确认</span>
                  </div>
                  <p>
                    请求：{batchConfirmResult.requested_count}，跳过：
                    {batchConfirmResult.skipped_count}
                  </p>
                </div>
              ) : null}

              <div className="sheet-list">
                <div className="section-title">
                  <h3>图纸台账</h3>
                  <span>
                    {sheetPage.total} 页，当前第 {sheetPage.page} / {sheetPage.total_pages || 1} 页
                  </span>
                </div>
                <div className="issue-summary">
                  <button type="button" onClick={() => applyQuickFilter({ has_error: true })}>错误 {issueSummary.error}</button>
                  <button type="button" onClick={() => applyQuickFilter({ has_warning: true })}>警告 {issueSummary.warning}</button>
                  <button type="button" onClick={() => applyQuickFilter({ issue_severity: "info" })}>信息 {issueSummary.info}</button>
                  <button type="button" onClick={() => applyQuickFilter({ missing_field: "drawing_no" })}>缺图号 {issueSummary.missingDrawingNo}</button>
                  <button type="button" onClick={() => applyQuickFilter({ missing_field: "drawing_name" })}>缺图名 {issueSummary.missingDrawingName}</button>
                  <button type="button" onClick={() => applyQuickFilter({ low_confidence: true })}>低可信 {issueSummary.lowConfidence}</button>
                  <button type="button" onClick={() => applyQuickFilter({ issue_code: "OCR_TEXT_EMPTY" })}>OCR 空文本 {issueSummary.ocrEmpty}</button>
                  <button type="button" onClick={() => applyQuickFilter({ issue_code: "CAD_BLOCK_ATTR_MISSING" })}>CAD 块属性缺失 {issueSummary.cadBlockAttrMissing}</button>
                </div>
                <div className="ledger-filters">
                  <input
                    value={sheetQuery.keyword ?? ""}
                    onChange={(event) => setSheetQuery({ ...sheetQuery, keyword: event.target.value })}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        updateSheetQuery({ keyword: sheetQuery.keyword });
                      }
                    }}
                    placeholder="搜索图号、图名、文件名"
                  />
                  <select
                    value={sheetQuery.discipline ?? ""}
                    onChange={(event) => updateSheetQuery({ discipline: event.target.value || undefined })}
                  >
                    <option value="">全部专业</option>
                    {["建筑", "结构", "给排水", "电气", "暖通", "弱电", "消防", "景观", "室外", "其他"].map((item) => (
                      <option value={item} key={item}>{item}</option>
                    ))}
                  </select>
                  <select
                    value={sheetQuery.status ?? ""}
                    onChange={(event) => updateSheetQuery({ status: event.target.value || undefined })}
                  >
                    <option value="">全部状态</option>
                    {["preprocessed", "recognized", "need_review", "failed", "confirmed"].map((item) => (
                      <option value={item} key={item}>{item}</option>
                    ))}
                  </select>
                  <select
                    value={sheetQuery.review_status ?? ""}
                    onChange={(event) => updateSheetQuery({ review_status: event.target.value || undefined })}
                  >
                    <option value="">全部校核</option>
                    <option value="unreviewed">未校核</option>
                    <option value="pending">待处理</option>
                    <option value="confirmed">已确认</option>
                  </select>
                  <select
                    value={sheetQuery.trust_level ?? ""}
                    onChange={(event) => updateSheetQuery({ trust_level: event.target.value || undefined })}
                  >
                    <option value="">全部等级</option>
                    {["A", "B", "C", "D"].map((item) => (
                      <option value={item} key={item}>{item}</option>
                    ))}
                  </select>
                  <select
                    value={sheetQuery.source_format ?? ""}
                    onChange={(event) => updateSheetQuery({ source_format: event.target.value || undefined })}
                  >
                    <option value="">全部格式</option>
                    <option value="pdf">PDF</option>
                    <option value="dxf">DXF</option>
                    <option value="dwg">DWG 转换图纸</option>
                  </select>
                  <select
                    value={sheetQuery.issue_severity ?? ""}
                    onChange={(event) => updateSheetQuery({ issue_severity: event.target.value || undefined })}
                  >
                    <option value="">全部问题</option>
                    <option value="error">error</option>
                    <option value="warning">warning</option>
                    <option value="info">info</option>
                  </select>
                  <select
                    value={sheetQuery.has_issue === undefined ? "" : String(sheetQuery.has_issue)}
                    onChange={(event) =>
                      updateSheetQuery({
                        has_issue: event.target.value === "" ? undefined : event.target.value === "true"
                      })
                    }
                  >
                    <option value="">是否有问题</option>
                    <option value="true">有问题</option>
                    <option value="false">无问题</option>
                  </select>
                  <select
                    value={sheetQuery.missing_field ?? ""}
                    onChange={(event) => updateSheetQuery({ missing_field: event.target.value || undefined })}
                  >
                    <option value="">字段完整性</option>
                    <option value="drawing_no">缺图号</option>
                    <option value="drawing_name">缺图名</option>
                    <option value="discipline">缺专业</option>
                    <option value="issue_date">缺日期</option>
                  </select>
                  <select
                    value={sheetQuery.sort_by ?? "created_at"}
                    onChange={(event) => updateSheetQuery({ sort_by: event.target.value })}
                  >
                    <option value="default">默认效率排序</option>
                    <option value="issue_count">问题数量</option>
                    <option value="confidence_score">可信度</option>
                    <option value="drawing_no">图纸编号</option>
                    <option value="discipline">专业排序</option>
                    <option value="file_name">文件名排序</option>
                    <option value="updated_at">最近修改时间</option>
                    <option value="unconfirmed_first">未确认优先</option>
                  </select>
                  <select
                    value={sheetQuery.sort_order ?? "desc"}
                    onChange={(event) => updateSheetQuery({ sort_order: event.target.value })}
                  >
                    <option value="desc">降序</option>
                    <option value="asc">升序</option>
                  </select>
                  <button type="button" onClick={() => updateSheetQuery({ keyword: sheetQuery.keyword })}>
                    搜索
                  </button>
                </div>
                <div className="quick-filters">
                  <button type="button" onClick={() => applyQuickFilter({})}>全部图纸</button>
                  <button type="button" onClick={() => applyQuickFilter({ review_status: "unreviewed" })}>未校核</button>
                  <button type="button" onClick={() => applyQuickFilter({ review_status: "confirmed" })}>已确认</button>
                  <button type="button" onClick={() => applyQuickFilter({ has_error: true })}>有错误</button>
                  <button type="button" onClick={() => applyQuickFilter({ has_warning: true })}>有警告</button>
                  <button type="button" onClick={() => applyQuickFilter({ low_confidence: true })}>低可信</button>
                  <button type="button" onClick={() => applyQuickFilter({ missing_field: "drawing_no" })}>缺图号</button>
                  <button type="button" onClick={() => applyQuickFilter({ missing_field: "drawing_name" })}>缺图名</button>
                  <button type="button" onClick={() => applyQuickFilter({ missing_field: "discipline" })}>缺专业</button>
                  <button type="button" onClick={() => applyQuickFilter({ missing_field: "issue_date" })}>缺日期</button>
                  <button type="button" onClick={() => applyQuickFilter({ source_format: "pdf" })}>PDF 图纸</button>
                  <button type="button" onClick={() => applyQuickFilter({ source_format: "dxf" })}>DXF 图纸</button>
                  <button type="button" onClick={() => applyQuickFilter({ source_format: "dwg" })}>DWG 转换图纸</button>
                  {["A", "B", "C", "D"].map((level) => (
                    <button type="button" key={level} onClick={() => applyQuickFilter({ trust_level: level })}>{level} 级</button>
                  ))}
                  <button type="button" onClick={() => applyQuickFilter({ low_confidence: true, review_status: "unreviewed" })}>低可信 + 未校核</button>
                  <button type="button" onClick={() => applyQuickFilter({ has_error: true, review_status: "unreviewed" })}>有错误 + 未校核</button>
                  <button type="button" onClick={() => applyQuickFilter({ missing_field: "drawing_no", review_status: "unreviewed" })}>缺图号 + 未校核</button>
                  <button type="button" onClick={() => applyQuickFilter({ source_format: "dxf", low_confidence: true })}>DXF + 低可信</button>
                <button type="button" onClick={() => applyQuickFilter({ source_format: "pdf", issue_code: "OCR_TEXT_EMPTY" })}>PDF + OCR 空文本</button>
                </div>
                <div className="inline-actions compact">
                  <button type="button" onClick={() => handleBatchConfirm("selected")}>确认当前筛选</button>
                  <button type="button" onClick={() => handleBatchConfirm("selected", "manual")}>确认已勾选 {selectedSheetIds.length}</button>
                  <button type="button" onClick={() => handleBatchConfirm("trust_a")}>确认 A 级</button>
                  <button type="button" onClick={() => handleBatchConfirm("trust_b_or_above")}>确认 A/B 级</button>
                  <button type="button" onClick={() => handleBatchConfirm("complete_fields")}>确认字段完整</button>
                </div>
                {projectNotice ? <p className="empty-state">{projectNotice}</p> : null}
                {sheetPage.total > 0 && sheets.length === 0 ? (
                  <EmptyState
                    title="当前筛选没有图纸"
                    description="可以清空筛选条件，或切换到全部图纸继续查看。"
                    actionLabel="查看全部图纸"
                    onAction={() => applyQuickFilter({})}
                  />
                ) : null}
                {sheets.length === 0 ? (
                  projectFiles.length === 0 ? (
                    <EmptyState
                      title="当前项目还没有导入图纸"
                      description="你可以先导入 PDF、DXF 或 DWG 文件开始生成图纸台账。"
                      actionLabel="导入图纸"
                      onAction={() => setImportOpen(true)}
                    />
                  ) : (
                    <EmptyState
                      title="暂无图纸页可显示"
                      description="如果已导入 PDF，请先生成图纸页；如果是 DXF 或 DWG，请执行 CAD pipeline。"
                      actionLabel={latestBatchId ? "执行下一步处理" : undefined}
                      onAction={latestBatchId ? () => {
                        if (canRunCadPipeline) {
                          handleRunCadPipeline(latestBatchId);
                        } else {
                          handleSplitBatch(latestBatchId);
                        }
                      } : undefined}
                    />
                  )
                ) : (
                  <div className="ledger-table">
                    <div className="ledger-row ledger-head">
                      <span>
                        <input
                          type="checkbox"
                          checked={sheets.length > 0 && sheets.every((sheet) => selectedSheetIds.includes(sheet.id))}
                          onChange={toggleCurrentPageSelection}
                        />
                      </span>
                      <span>缩略图</span>
                      <span>图纸编号</span>
                      <span>图纸名称</span>
                      <span>专业</span>
                      <span>版本</span>
                      <span>日期</span>
                      <span>格式</span>
                      <span>文件名</span>
                      <span>页码</span>
                      <span>等级</span>
                      <span>评分</span>
                      <span>状态</span>
                      <span>校核</span>
                      <span>问题</span>
                      <span>操作</span>
                    </div>
                    {sheets.map((sheet) => (
                      <article className="ledger-row" key={sheet.id}>
                        <span>
                          <input
                            type="checkbox"
                            checked={selectedSheetIds.includes(sheet.id)}
                            onChange={() => toggleSelectedSheet(sheet.id)}
                          />
                        </span>
                        <span>
                          {sheet.thumbnail_path ? (
                            <img
                              src={`/api/sheets/${sheet.id}/thumbnail`}
                              alt={`${sheet.original_file_name} 第 ${sheet.page_no} 页`}
                              onError={(event) => {
                                event.currentTarget.style.display = "none";
                              }}
                            />
                          ) : sheet.source_format === "dxf" ? (
                            <span className="thumb-placeholder small">
                              CAD 预览：{cadPreviewStatusLabel(sheet.cad_preview_status, Boolean(sheet.cad_preview_path), sheet.cad_preview_error_code)}
                            </span>
                          ) : (
                            <span className="thumb-placeholder small">图片不可用或文件缺失。</span>
                          )}
                        </span>
                        <span>{sheet.drawing_no || "-"}</span>
                        <span>{sheet.drawing_name || "-"}</span>
                        <span>{sheet.discipline || "-"}</span>
                        <span>{sheet.version || "-"}</span>
                        <span>{sheet.issue_date || "-"}</span>
                        <span>{sheet.source_format.toUpperCase()}</span>
                        <span>{sheet.original_file_name}</span>
                        <span>{sheet.page_no}</span>
                        <span>{sheet.trust_level || "-"}</span>
                        <span>{sheet.confidence_score ?? "-"}</span>
                        <span>{statusLabel(sheet.status)}</span>
                        <span>{sheet.review_status}</span>
                        <span>{sheet.issue_count}</span>
                        <span className="ledger-actions">
                          <button type="button" onClick={() => handleOpenSheetDetail(sheet.id)}>
                            查看详情
                          </button>
                          <button type="button" onClick={() => openReviewWorkbench(sheet)}>
                            校核
                          </button>
                          {sheet.source_format === "pdf" ? (
                            <button type="button" onClick={() => setPreviewSheet(sheet)}>
                              查看预览
                            </button>
                          ) : (
                            <button type="button" onClick={() => setPreviewSheet(sheet)}>
                              {sheet.cad_preview_status === "success" && sheet.cad_preview_path ? "查看 CAD 预览" : "CAD 预览入口"}
                            </button>
                          )}
                          <button type="button" onClick={() => updateSheetQuery({ has_issue: true })}>
                            查看问题
                          </button>
                          {sheet.source_format === "pdf" ? (
                            <>
                              {sheet.title_crop_status === "success" ? (
                                <button type="button" onClick={() => setPreviewSheet(sheet)}>
                                  查看标题栏
                                </button>
                              ) : (
                                <button type="button" onClick={() => handleCropSheetTitle(sheet.id)}>
                                  生成标题栏裁剪
                                </button>
                              )}
                              <button type="button" onClick={() => handleExtractSheetText(sheet.id)}>
                                提取 PDF 文本
                              </button>
                              <button type="button" onClick={() => handleOcrSheetTitle(sheet.id)}>
                                识别标题栏 OCR
                              </button>
                              <button type="button" onClick={() => handleLoadRuns(sheet.id)}>
                                查看运行记录
                              </button>
                              <button
                                type="button"
                                onClick={() => handleGenerateSheetCandidates(sheet.id)}
                              >
                                生成候选值
                              </button>
                              <button type="button" onClick={() => handleLoadCandidates(sheet.id)}>
                                查看候选值
                              </button>
                              <button type="button" onClick={() => handleFuseSheetFields(sheet.id)}>
                                生成推荐字段
                              </button>
                              <button type="button" onClick={() => handleLoadFieldValues(sheet.id)}>
                                查看推荐字段
                              </button>
                            </>
                          ) : (
                            <>
                              <span>
                                {sheet.status === "cad_parsed"
                                  ? "DXF 原始实体已解析。"
                                  : ["recognized", "need_review", "confirmed"].includes(sheet.status)
                                    ? "推荐字段已生成。"
                                  : "DXF 图纸页已创建，尚未解析 DXF 实体。"}
                              </span>
                              <button type="button" disabled={busyAction === `parse-${sheet.file_id}`} onClick={() => handleParseDxfFile(sheet.file_id)}>
                                {busyAction === `parse-${sheet.file_id}` ? "解析中..." : "解析 DXF"}
                              </button>
                              <button
                                type="button"
                                disabled={busyAction === `cad-summary-${sheet.id}`}
                                onClick={() => handleLoadCadParseSummary(sheet.id)}
                              >
                                {busyAction === `cad-summary-${sheet.id}` ? "加载摘要中..." : "查看 CAD 解析摘要"}
                              </button>
                              <button
                                type="button"
                                disabled={busyAction === `cad-preview-${sheet.id}`}
                                onClick={() => handleGenerateCadPreview(sheet.id)}
                              >
                                {busyAction === `cad-preview-${sheet.id}`
                                  ? "生成预览中..."
                                  : sheet.cad_preview_status === "failed"
                                    ? "重新生成 CAD 预览"
                                    : sheet.cad_preview_status === "success"
                                      ? "刷新 CAD 预览"
                                      : "生成 CAD 预览"}
                              </button>
                              {sheet.cad_preview_status === "failed" ? (
                                <span>{sheet.cad_preview_error_code || "CAD_PREVIEW_RENDER_FAILED"}</span>
                              ) : null}
                              <button
                                type="button"
                                disabled={busyAction === `candidates-${sheet.id}`}
                                onClick={() => handleGenerateSheetCandidates(sheet.id)}
                              >
                                {busyAction === `candidates-${sheet.id}` ? "生成中..." : "生成 DXF 候选值"}
                              </button>
                              <button type="button" onClick={() => handleLoadCandidates(sheet.id)}>
                                查看候选值
                              </button>
                              <button type="button" disabled={busyAction === `fusion-${sheet.id}`} onClick={() => handleFuseSheetFields(sheet.id)}>
                                {busyAction === `fusion-${sheet.id}` ? "生成中..." : "生成推荐字段"}
                              </button>
                              <button type="button" onClick={() => handleLoadRuns(sheet.id)}>
                                查看运行记录
                              </button>
                            </>
                          )}
                        </span>
                      </article>
                    ))}
                  </div>
                )}
                <div className="pagination">
                  <button
                    type="button"
                    disabled={sheetPage.page <= 1}
                    onClick={() => updateSheetQuery({ page: sheetPage.page - 1 })}
                  >
                    上一页
                  </button>
                  <span>
                    第 {sheetPage.page} 页 / 共 {sheetPage.total_pages || 1} 页，合计 {sheetPage.total}
                  </span>
                  <select
                    value={sheetPage.page_size}
                    onChange={(event) => updateSheetQuery({ page_size: Number(event.target.value), page: 1 })}
                  >
                    {[10, 20, 50, 100].map((size) => (
                      <option value={size} key={size}>{size} / 页</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={sheetPage.page >= sheetPage.total_pages}
                    onClick={() => updateSheetQuery({ page: sheetPage.page + 1 })}
                  >
                    下一页
                  </button>
                </div>
              </div>

              {runsSheetId ? (
                <div className="sheet-list">
                  <div className="section-title">
                    <h3>识别运行记录</h3>
                    <span>Sheet {runsSheetId}</span>
                  </div>
                  {recognitionRuns.length === 0 ? (
                    <EmptyState
                      title="暂无识别运行记录"
                      description="生成标题栏裁剪、提取 PDF 文本或运行 OCR 后，这里会显示处理记录。"
                    />
                  ) : (
                    <div className="file-list">
                      {recognitionRuns.map((run) => (
                        <div className="file-row run-row" key={run.id}>
                          <span>{run.run_type}</span>
                          <span>{run.status}</span>
                          <span>{run.engine_name}</span>
                          <span>{formatDate(run.finished_at)}</span>
                          <span>{run.error_code || "-"}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}

              {candidatesSheetId ? (
                <div className="sheet-list">
                  <div className="section-title">
                    <h3>候选值</h3>
                    <span>Sheet {candidatesSheetId}</span>
                  </div>
                  {candidates.length === 0 ? (
                    <EmptyState
                      title="图纸还没有候选值"
                      description="请先生成候选值；如果仍为空，可以在校核工作台人工填写关键字段。"
                      actionLabel={latestBatchId ? "生成候选值" : undefined}
                      onAction={latestBatchId ? () => handleGenerateBatchCandidates(latestBatchId) : undefined}
                    />
                  ) : (
                    <CandidateGroups candidates={candidates} />
                  )}
                </div>
              ) : null}

              {fieldValuesSheetId ? (
                <div className="sheet-list">
                  <div className="section-title">
                    <h3>推荐字段与证据</h3>
                    <span>Sheet {fieldValuesSheetId}</span>
                  </div>
                  {fieldValues.length === 0 ? (
                    <EmptyState
                      title="暂无推荐字段"
                      description="请先生成候选值并生成推荐字段；也可以在校核工作台人工填写。"
                      actionLabel={latestBatchId ? "生成推荐字段" : undefined}
                      onAction={latestBatchId ? () => handleFuseBatchFields(latestBatchId) : undefined}
                    />
                  ) : (
                    <FieldValueList values={fieldValues} evidence={fieldEvidence} />
                  )}
                </div>
              ) : null}

              <div className="sheet-list">
                <div className="section-title">
                  <h3>问题清单</h3>
                  <span>{issues.length} 个 open 问题</span>
                </div>
                {issues.length === 0 ? (
                  <EmptyState
                    title="暂无问题清单"
                    description="当前项目没有打开的问题。可以继续校核，或导出 Excel。"
                    actionLabel={canExportProject ? "导出 Excel" : undefined}
                    onAction={canExportProject ? () => handleExportExcel(true) : undefined}
                  />
                ) : (
                  <div className="issue-list">
                    {issues.slice(0, 12).map((issue) => (
                      <article className="issue-row" key={issue.id}>
                        <strong>{issue.issue_code}</strong>
                        <span>{issue.severity}</span>
                        <span>Sheet {issue.sheet_id}</span>
                        <p>{issue.message}</p>
                        <p>{issue.suggestion}</p>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <EmbeddedTablesSection sheetId={reviewSheet?.id ?? null} />

              {reviewSheet ? (
                <div className="review-workbench">
                  <div className="section-title">
                    <h3>校核工作台</h3>
                    <span>
                      {reviewSheet.original_file_name} 第 {reviewSheet.page_no} 页 / Ctrl+S 保存 / Ctrl+Enter 保存并确认
                    </span>
                  </div>
                  <ErrorNotice message={reviewError} />
                  {reviewMessage ? <p className="success-message">{reviewMessage}</p> : null}
                  <div className="review-layout">
                    <aside className="review-list">
                      <button type="button" onClick={() => applyQuickFilter({})}>全部</button>
                      <button type="button" onClick={() => applyQuickFilter({ review_status: "unreviewed" })}>未校核</button>
                      <button type="button" onClick={() => applyQuickFilter({ has_error: true })}>有错误</button>
                      <button type="button" onClick={() => applyQuickFilter({ has_warning: true })}>有警告</button>
                      <button type="button" onClick={() => applyQuickFilter({ low_confidence: true })}>低可信</button>
                      <button type="button" onClick={() => applyQuickFilter({ missing_field: "drawing_no" })}>缺图号</button>
                      <button type="button" onClick={() => applyQuickFilter({ missing_field: "drawing_name" })}>缺图名</button>
                      <button type="button" onClick={() => applyQuickFilter({ review_status: "confirmed" })}>已确认</button>
                      <button type="button" onClick={() => handleBatchConfirm("selected")}>确认当前筛选</button>
                    </aside>
                    <section className="review-preview">
                      {reviewSheet.preview_path ? (
                        <img src={`/api/sheets/${reviewSheet.id}/preview`} alt="图纸预览" />
                      ) : (
                        <p className="empty-state">图片不可用或文件缺失。</p>
                      )}
                      {reviewSheet.title_crop_status === "success" ? (
                        <img src={`/api/sheets/${reviewSheet.id}/title-crop`} alt="标题栏裁剪图" />
                      ) : (
                        <p className="empty-state">图片不可用或文件缺失。</p>
                      )}
                    </section>
                    <section className="review-panel">
                      <h4>字段校核</h4>
                      {fieldValues.length === 0 ? (
                        <EmptyState
                          title="当前图纸暂无推荐字段"
                          description="可以先生成候选值和推荐字段，也可以直接人工填写后确认。"
                        />
                      ) : null}
                      {["drawing_no", "drawing_name", "discipline", "version", "issue_date"].map((field) => {
                        const value = fieldValues.find((item) => item.field_name === field);
                        const fieldCandidates = candidates.filter((candidate) => candidate.field_name === field);
                        const recommended = recommendedCandidate(field, candidates);
                        return (
                          <div className="review-field" key={field}>
                            <label>
                              {fieldNameLabel(field)}
                              <input
                                value={reviewFields[field] ?? ""}
                                onChange={(event) =>
                                  setReviewFields({ ...reviewFields, [field]: event.target.value })
                                }
                              />
                            </label>
                            <div className="source-note">
                              <strong>来源：{sourceTypeLabel(value?.final_source ?? "-")}</strong>
                              <span>置信度：{value?.confidence ?? "-"}</span>
                              <span>说明：{fieldSourceDescription(value, fieldEvidence)}</span>
                              <span>人工确认：{value?.is_reviewed ? "是" : "否"}</span>
                            </div>
                            <div className="inline-actions compact">
                              <button type="button" onClick={() => handleAdoptRecommendedField(field)} disabled={!recommended}>采用推荐值</button>
                              <button type="button" className="ghost" onClick={() => handleClearReviewField(field)}>清空</button>
                              <button type="button" className="ghost" onClick={() => handleRestoreRecommendedField(field)}>恢复机器推荐</button>
                            </div>
                            {fieldCandidates.length > 0 ? (
                              <div className="candidate-chips">
                                {fieldCandidates.slice(0, 4).map((candidate) => (
                                  <button
                                    type="button"
                                    className={recommended?.id === candidate.id ? "recommended" : "ghost"}
                                    key={candidate.id}
                                    onClick={() => handleApplyCandidateValue(candidate)}
                                    title={`${sourceTypeLabel(candidate.source_type)} / ${candidate.confidence} / ${candidate.raw_text}`}
                                  >
                                    {candidate.normalized_value || candidate.candidate_value}
                                  </button>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                      <label>
                        备注
                        <textarea value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} rows={2} />
                      </label>
                      <div className="inline-actions">
                        <button type="button" onClick={handleSaveReviewFields} disabled={reviewSaveState === "saving"}>
                          {reviewSaveState === "saving" ? "保存中..." : "保存字段修改"}
                        </button>
                        <button type="button" onClick={handleConfirmReviewSheet}>确认本图纸</button>
                        <button type="button" onClick={handleSaveAndConfirmReviewSheet}>保存并确认</button>
                        <button
                          type="button"
                          onClick={() => {
                            const next = sheets.find((sheet) => sheet.status === "need_review" && sheet.id !== reviewSheet.id);
                            if (next) openReviewWorkbench(next);
                          }}
                        >
                          下一张待校核
                        </button>
                        <button type="button" className="ghost" onClick={() => setReviewSheet(null)}>返回台账</button>
                      </div>
                    </section>
                  </div>
                  <div className="review-bottom">
                    <section>
                      <h4>候选值</h4>
                      {candidates.map((candidate) => (
                        <article className="candidate-row" key={candidate.id}>
                          <strong>{fieldNameLabel(candidate.field_name)}: {candidate.candidate_value}</strong>
                          <span>标准化：{candidate.normalized_value || "-"}</span>
                          <span>来源：{sourceTypeLabel(candidate.source_type)} / 置信度：{candidate.confidence}</span>
                          <span>原始文本：{candidate.raw_text || "-"}</span>
                          <span>{recommendedCandidate(candidate.field_name, candidates)?.id === candidate.id ? "推荐值" : "候选值"}</span>
                          <div className="inline-actions compact">
                            <button type="button" onClick={() => handleApplyCandidateValue(candidate)}>填入字段</button>
                            <button type="button" className="ghost" onClick={() => handleAdoptCandidate(candidate)}>立即采用并保存</button>
                          </div>
                        </article>
                      ))}
                    </section>
                    <section>
                      <h4>问题列表</h4>
                      {issues.filter((issue) => issue.sheet_id === reviewSheet.id).map((issue) => (
                        <article className="issue-row" key={issue.id}>
                          <strong>{issue.issue_code}</strong>
                          <span>{issue.severity}</span>
                          <span>{issue.status}</span>
                          <p>{issue.message}</p>
                          <p>{issue.suggestion}</p>
                          <div className="inline-actions">
                            <button type="button" onClick={() => handleUpdateIssueStatus(issue.id, "resolved")}>标记解决</button>
                            <button type="button" onClick={() => handleUpdateIssueStatus(issue.id, "ignored")}>忽略</button>
                            <button type="button" onClick={() => handleUpdateIssueStatus(issue.id, "reopened")}>重新打开</button>
                          </div>
                        </article>
                      ))}
                    </section>
                    <section>
                      <h4>审计日志</h4>
                      {auditLogs.length === 0 ? (
                        <EmptyState
                          title="暂无审计日志"
                          description="保存字段、采用候选值或确认图纸后，这里会记录操作。"
                        />
                      ) : (
                        <div className="file-list">
                          {auditLogs.map((log) => (
                            <div className="file-row run-row" key={log.id}>
                              <span>{log.action_type}</span>
                              <span>{log.field_name || "-"}</span>
                              <span>{log.old_value || "-"}</span>
                              <span>{log.new_value || "-"}</span>
                              <span>{formatDate(log.created_at)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </section>
                  </div>
                </div>
              ) : null}

              <div className="export-center">
                <div className="section-title">
                  <h3>导出中心</h3>
                  <span>Excel 图纸台账</span>
                </div>
                <ErrorNotice message={exportError} />
                <div className="inline-actions">
                  <button type="button" onClick={handleCheckExport}>检查导出状态</button>
                  <button
                    type="button"
                    onClick={() => handleExportExcel(true)}
                    disabled={!!exportCheck && !exportCheck.can_export}
                  >
                    导出 Excel 台账
                  </button>
                </div>
                {exportCheck ? (
                  <div className="export-check">
                    <h4>导出前检查</h4>
                    <strong>
                      {!exportCheck.can_export
                        ? "当前项目没有图纸，无法导出 Excel 台账。"
                        : exportCheck.is_complete_ledger
                          ? "当前项目可导出正式台账。"
                          : exportCheck.summary_message}
                    </strong>
                    <dl>
                      <div><dt>图纸总数</dt><dd>{exportCheck.sheet_count}</dd></div>
                      <div><dt>未校核</dt><dd>{exportCheck.unconfirmed_count}</dd></div>
                      <div><dt>缺图号</dt><dd>{exportCheck.empty_drawing_no_count}</dd></div>
                      <div><dt>缺图名</dt><dd>{exportCheck.empty_drawing_name_count}</dd></div>
                      <div><dt>错误</dt><dd>{exportCheck.open_error_count}</dd></div>
                      <div><dt>警告</dt><dd>{exportCheck.open_warning_count}</dd></div>
                      <div><dt>D 级</dt><dd>{exportCheck.trust_level_d_count}</dd></div>
                    </dl>
                    {exportCheck.warnings.length > 0 ? (
                      <ul>
                        {exportCheck.warnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
                {exportResult ? (
                  <div className="success-message export-success">
                    <strong>Excel 台账已生成</strong>
                    <span>文件名：{exportResult.file_name}</span>
                    <span>图纸总台账：{exportResult.ledger_row_count} 行</span>
                    <span>问题清单：{exportResult.issue_row_count} 行</span>
                    <span>建议创建项目备份，便于迁移或回退到当前台账状态。</span>
                    {exportResult.warning_count > 0 ? (
                      <span>导出已完成，但存在未校核或低可信图纸，请在 Excel 中重点复核。</span>
                    ) : null}
                    <div className="inline-actions">
                      <button type="button" onClick={() => downloadExport(exportResult.export_id)}>下载</button>
                      <button type="button" className="ghost" onClick={handleCreateBackup} disabled={backupBusy}>
                        {backupBusy ? "正在备份..." : "创建项目备份"}
                      </button>
                    </div>
                  </div>
                ) : null}
                <div className="sheet-list">
                  <div className="section-title">
                    <h3>导出历史</h3>
                    <span>{exportRecords.length} 条</span>
                  </div>
                  {exportRecords.length === 0 ? (
                    <EmptyState
                      title="暂无导出记录"
                      description="校核完成后导出 Excel，这里会保留最近生成的台账记录。"
                      actionLabel={canExportProject ? "导出 Excel" : undefined}
                      onAction={canExportProject ? () => handleExportExcel(true) : undefined}
                    />
                  ) : (
                    <div className="file-list">
                      {exportRecords.map((record) => (
                        <div className="file-row export-row" key={record.export_id}>
                          <span>{record.file_name}</span>
                          <span>{formatDate(record.created_at)}</span>
                          <span>{record.sheet_count} 张</span>
                          <span>{record.issue_count} 问题</span>
                          <span>{record.include_unconfirmed ? "含未确认" : "已确认"}</span>
                          <span>{record.has_open_errors ? "有 error" : "无 error"}</span>
                          <button type="button" onClick={() => downloadExport(record.export_id)}>下载</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="home-workbench">
              <div className="home-grid">
                <section className="home-panel recent-home">
                  <div className="section-title">
                    <h3>最近项目</h3>
                    <span>{projects.slice(0, 5).length} 条</span>
                  </div>
                  {projects.length === 0 ? (
                    <EmptyState
                      title="还没有项目"
                      description="先在左侧新建项目，再导入 PDF、DXF 或 DWG 文件开始日常台账工作。"
                      actionLabel="新建项目"
                      onAction={() => document.querySelector<HTMLInputElement>(".project-form input")?.focus()}
                    />
                  ) : (
                    <div className="recent-project-cards">
                      {projects.slice(0, 5).map((project) => (
                        <article className="recent-project-card" key={project.id}>
                          <div>
                            <strong title={project.name}>{project.name}</strong>
                            <span>最近打开：{project.last_opened_at ? formatDate(project.last_opened_at) : "尚未打开"}</span>
                          </div>
                          <dl>
                            <div><dt>图纸</dt><dd>{project.stats.sheet_count}</dd></div>
                            <div><dt>未校核</dt><dd>{project.stats.need_review_count}</dd></div>
                            <div><dt>问题</dt><dd>{project.stats.issue_count}</dd></div>
                          </dl>
                          <button type="button" onClick={() => handleOpenProject(project.id)}>打开项目</button>
                        </article>
                      ))}
                    </div>
                  )}
                </section>

                <section className="home-panel quick-home">
                  <div className="section-title">
                    <div>
                      <p className="eyebrow">快捷操作</p>
                      <h3>从这里开始</h3>
                    </div>
                    <span>{healthError ? "后端未连接" : "本地可用"}</span>
                  </div>
                  <div className="quick-action-grid">
                    <QuickActionButton action={{ label: "快速新建项目", onClick: () => document.querySelector<HTMLInputElement>(".project-form input")?.focus(), primary: true }} />
                    <QuickActionButton
                      action={{
                        label: "打开最近项目",
                        onClick: () => projects[0] && handleOpenProject(projects[0].id),
                        disabled: projects.length === 0,
                        reason: "暂无最近项目"
                      }}
                    />
                    <QuickActionButton
                      action={{
                        label: "系统健康检查",
                        onClick: handleRunSystemHealthCheck,
                        disabled: maintenanceBusy === "system-health",
                        reason: maintenanceBusy === "system-health" ? "正在检查" : undefined,
                        busy: maintenanceBusy === "system-health"
                      }}
                    />
                  </div>
                  {healthError ? (
                    <div className="connection-error">
                      <strong>后端未连接</strong>
                      <span>请确认本地服务已启动，再进行项目操作。</span>
                    </div>
                  ) : null}
                </section>
              </div>

              <section className="flow-guide">
                <div><strong>PDF 流程</strong><span>上传 PDF → 拆页 → 识别 → 校核 → 导出 Excel</span></div>
                <div><strong>DXF 流程</strong><span>上传 DXF → CAD 解析 → 识别 → CAD 预览 → 校核 → 导出 Excel</span></div>
                <div><strong>DWG 流程</strong><span>上传 DWG → 转 DXF → CAD 解析 → 校核 → 导出 Excel</span></div>
              </section>
            </div>
          )}
        </section>
      </section>

      <footer className="app-footer">
        <span>版本：{health?.version ?? APP_VERSION}</span>
        <span>本地数据目录：app_data</span>
      </footer>

      {previewSheet ? (
        <div className="preview-modal" role="dialog" aria-modal="true">
          <div className="preview-dialog">
            <div className="section-title">
              <h3>
                {previewSheet.original_file_name} 第 {previewSheet.page_no} 页
              </h3>
              <button type="button" className="ghost" onClick={() => setPreviewSheet(null)}>
                关闭
              </button>
            </div>
            <div className="preview-columns">
              <div>
                {previewSheet.source_format === "pdf" ? (
                  <>
                    <h4>整页预览</h4>
                    {previewSheet.preview_path ? (
                      <img
                        src={`/api/sheets/${previewSheet.id}/preview`}
                        alt={`${previewSheet.original_file_name} 第 ${previewSheet.page_no} 页预览`}
                      />
                    ) : (
                      <EmptyState
                        title="整页预览不可用"
                        description="预览文件可能缺失。请重新生成图纸页预览，或检查 app_data 是否完整。"
                      />
                    )}
                  </>
                ) : (
                  <>
                    <h4>CAD 图形预览</h4>
                    <p className="empty-state">
                      CAD 预览仅用于辅助查看，可能与专业 CAD 软件显示效果不完全一致。
                    </p>
                    <CadPreviewViewer
                      imageUrl={
                        previewSheet.cad_preview_status === "success" && previewSheet.cad_preview_path
                          ? getCadPreviewImageUrl(previewSheet.id)
                          : null
                      }
                      fileName={previewSheet.original_file_name}
                      status={previewSheet.cad_preview_status || "pending"}
                      errorCode={previewSheet.cad_preview_error_code}
                      errorMessage={previewSheet.cad_preview_error_message}
                      isGenerating={busyAction === `cad-preview-${previewSheet.id}`}
                      onRegenerate={() => handleGenerateCadPreview(previewSheet.id)}
                    />
                  </>
                )}
              </div>
              {previewSheet.source_format === "pdf" ? (
              <div>
                <h4>标题栏裁剪图</h4>
                {previewSheet.title_crop_status === "success" ? (
                  <img
                    src={`/api/sheets/${previewSheet.id}/title-crop`}
                    alt={`${previewSheet.original_file_name} 第 ${previewSheet.page_no} 页标题栏`}
                  />
                ) : previewSheet.title_crop_status === "failed" ? (
                  <p className="empty-state">
                    {previewSheet.title_crop_error_code}：
                    {previewSheet.title_crop_error_message}
                  </p>
                ) : (
                  <div className="modal-actions">
                    <EmptyState
                      title="尚未生成标题栏裁剪图"
                      description="先生成标题栏裁剪图，再提取或识别标题栏内容。"
                    />
                    <button type="button" onClick={() => handleCropSheetTitle(previewSheet.id)}>
                      生成标题栏裁剪
                    </button>
                  </div>
                )}
                <div className="modal-actions">
                  <button type="button" onClick={() => handleExtractSheetText(previewSheet.id)}>
                    提取 PDF 文本
                  </button>
                  <button type="button" onClick={() => handleOcrSheetTitle(previewSheet.id)}>
                    识别标题栏 OCR
                  </button>
                  <button type="button" onClick={() => handleLoadRuns(previewSheet.id)}>
                    查看运行记录
                  </button>
                  <button
                    type="button"
                    onClick={() => handleGenerateSheetCandidates(previewSheet.id)}
                  >
                    生成候选值
                  </button>
                  <button type="button" onClick={() => handleLoadCandidates(previewSheet.id)}>
                    查看候选值
                  </button>
                  <button type="button" onClick={() => handleFuseSheetFields(previewSheet.id)}>
                    生成推荐字段
                  </button>
                  <button type="button" onClick={() => handleLoadFieldValues(previewSheet.id)}>
                    查看推荐字段
                  </button>
                </div>
              </div>
              ) : (
              <div>
                <h4>CAD 预览状态</h4>
                <p className="empty-state">
                  DXF 图纸或 DWG 转 DXF 后的图纸可以生成轻量 PNG 预览。预览失败不会影响候选值、校核或 Excel 导出。
                </p>
                <div className="modal-actions">
                  <button
                    type="button"
                    disabled={busyAction === `parse-${previewSheet.file_id}`}
                    onClick={() => handleParseDxfFile(previewSheet.file_id)}
                  >
                    {busyAction === `parse-${previewSheet.file_id}` ? "解析中..." : "解析 DXF"}
                  </button>
                  <button
                    type="button"
                    disabled={busyAction === `cad-summary-${previewSheet.id}`}
                    onClick={() => handleLoadCadParseSummary(previewSheet.id)}
                  >
                    {busyAction === `cad-summary-${previewSheet.id}` ? "加载摘要中..." : "查看 CAD 解析摘要"}
                  </button>
                  <button type="button" onClick={() => handleGenerateSheetCandidates(previewSheet.id)}>
                    生成候选值
                  </button>
                  <button type="button" onClick={() => handleFuseSheetFields(previewSheet.id)}>
                    生成推荐字段
                  </button>
                </div>
              </div>
              )}
            </div>
            {detailSheet?.id === previewSheet.id ? (
              <div className="detail-readonly">
                <section>
                  <h4>推荐字段</h4>
                  {fieldValues.length === 0 ? (
                    <EmptyState
                      title="暂无推荐字段"
                      description="生成候选值和推荐字段后，这里会展示系统建议值与证据。"
                    />
                  ) : (
                    <FieldValueList values={fieldValues} evidence={fieldEvidence} />
                  )}
                </section>
                <section>
                  <h4>候选值</h4>
                  {candidates.length === 0 ? (
                    <EmptyState
                      title="暂无候选值"
                      description="请先生成候选值；如果图纸文字较少，可以在校核工作台人工填写。"
                    />
                  ) : (
                    <CandidateGroups candidates={candidates} />
                  )}
                </section>
                <section>
                  <h4>识别运行记录</h4>
                  {recognitionRuns.length === 0 ? (
                    <EmptyState
                      title="暂无运行记录"
                      description="执行文本提取、OCR 或候选值生成后，这里会显示运行记录。"
                    />
                  ) : (
                    <div className="file-list">
                      {recognitionRuns.map((run) => (
                        <div className="file-row run-row" key={run.id}>
                          <span>{run.run_type}</span>
                          <span>{run.status}</span>
                          <span>{run.engine_name}</span>
                          <span>{formatDate(run.finished_at)}</span>
                          <span>{run.error_code || "-"}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
                <section>
                  <h4>问题</h4>
                  {issues.filter((issue) => issue.sheet_id === previewSheet.id).length === 0 ? (
                    <EmptyState
                      title="暂无问题"
                      description="当前图纸没有打开的问题，可以继续校核或确认。"
                    />
                  ) : (
                    <div className="issue-list">
                      {issues
                        .filter((issue) => issue.sheet_id === previewSheet.id)
                        .map((issue) => (
                          <article className="issue-row" key={issue.id}>
                            <strong>{issue.issue_code}</strong>
                            <span>{issue.severity}</span>
                            <span>{issue.status}</span>
                            <p>{issue.message}</p>
                            <p>{issue.suggestion}</p>
                          </article>
                        ))}
                    </div>
                  )}
                </section>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {cadParseSummary ? (
        <div className="preview-modal" role="dialog" aria-modal="true">
          <div className="preview-dialog">
            <div className="section-title">
              <h3>CAD 解析摘要</h3>
              <button type="button" className="ghost" onClick={() => setCadParseSummary(null)}>
                关闭
              </button>
            </div>
            <div className="preview-columns">
              <div>
                <h4>解析状态</h4>
                <p>解析状态：已解析</p>
                <p>CAD JSON：{cadParseSummary.output_path}</p>
                <p>
                  TEXT：{cadParseSummary.counts.text_count ?? 0}，MTEXT：
                  {cadParseSummary.counts.mtext_count ?? 0}，INSERT：
                  {cadParseSummary.counts.insert_count ?? 0}，ATTRIB：
                  {cadParseSummary.counts.attrib_count ?? 0}，图层：
                  {cadParseSummary.counts.layer_count ?? 0}
                </p>
                {cadParseSummary.warnings.length > 0 ? (
                  <p className="empty-state">Warnings：{cadParseSummary.warnings.join(", ")}</p>
                ) : null}
                <h4>图层列表</h4>
                <p>{cadParseSummary.layers.join("、") || "-"}</p>
              </div>
              <div>
                <h4>TEXT</h4>
                <ul>
                  {cadParseSummary.sample_texts.map((item, index) => (
                    <li key={`text-${index}`}>
                      {String(item.clean_text ?? item.raw_text ?? "")} / {String(item.layer ?? "-")} / {formatPoint(item.insert)}
                    </li>
                  ))}
                </ul>
                <h4>MTEXT</h4>
                <ul>
                  {cadParseSummary.sample_mtexts.map((item, index) => (
                    <li key={`mtext-${index}`}>
                      {String(item.clean_text ?? item.raw_text ?? "")} / {String(item.layer ?? "-")} / {formatPoint(item.insert)}
                    </li>
                  ))}
                </ul>
                <h4>ATTRIB</h4>
                <ul>
                  {cadParseSummary.sample_attribs.map((item, index) => (
                    <li key={`attrib-${index}`}>
                      {String(item.tag ?? "")} {String(item.clean_text ?? item.raw_text ?? "")} / {String(item.layer ?? "-")}
                    </li>
                  ))}
                </ul>
                {cadParseSummary.sample_texts.length === 0 && cadParseSummary.sample_mtexts.length === 0 && cadParseSummary.sample_attribs.length === 0 ? (
                  <EmptyState
                    title="暂无可展示的 CAD 文字"
                    description="CAD 文件可以读取，但没有提取到文字或块属性。可返回项目页人工校核字段。"
                  />
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
