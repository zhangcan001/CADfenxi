import React from "react";
import ReactDOM from "react-dom/client";
import {
  createProject,
  deleteProject,
  getProject,
  listProjects,
  updateProject,
  type Project
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
  runCadPipeline,
  type CadPipelineRequest,
  type CadPipelineResponse,
  type CadPipelineStep
} from "./api/cadPipeline";
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
  listRecognitionRuns,
  ocrBatchTitles,
  ocrSheetTitle,
  type BatchRecognitionResult,
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
  checkExport,
  downloadExport,
  exportExcel,
  listExports,
  type ExportCheckResult,
  type ExportExcelResult,
  type ExportRecord
} from "./api/exports";
import "./styles.css";
import type { HealthResponse } from "./types";
import { APP_VERSION } from "./constants";
import {
  drawingFileLabel,
  errorCodeMessage,
  fieldNameLabel,
  fieldSourceDescription,
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
import { CandidateGroups } from "./components/CandidateGroups";
import { FieldValueList } from "./components/FieldValueList";
import { Metric } from "./components/Metric";
import { ProjectsAside } from "./components/ProjectsAside";

function App() {
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = React.useState(false);
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = React.useState<Project | null>(null);
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
  const [busyAction, setBusyAction] = React.useState("");
  const [previewSheet, setPreviewSheet] = React.useState<DrawingSheet | null>(null);
  const [titleCropResult, setTitleCropResult] = React.useState<BatchTitleCropResult | null>(null);
  const [titleCropError, setTitleCropError] = React.useState("");
  const [recognitionResult, setRecognitionResult] =
    React.useState<BatchRecognitionResult | null>(null);
  const [recognitionError, setRecognitionError] = React.useState("");
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
        setProjectFiles([]);
        setSheets([]);
        setSheetPage({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
        setImportResult(null);
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
        setEditing(false);
        setEditName(project.name);
        setEditDescription(project.description ?? "");
        loadProjectFiles(project.id);
        loadProjectSheets(project.id);
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
          setProjectFiles([]);
          setSheets([]);
          setSheetPage({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
        }
      })
      .catch(() => setProjectError("项目删除失败"));
  };

  const handleSelectFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    const invalidFiles = files.filter((file) => !isSupportedDrawingFile(file.name));
    const drawingFiles = files.filter((file) => isSupportedDrawingFile(file.name));
    setSelectedFiles(drawingFiles);
    setImportResult(null);
    setImportError(
      invalidFiles.length > 0
          ? "当前仅支持 PDF、DXF 和 DWG 文件。"
        : ""
    );
  };

  const handleUpload = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedProject) {
      return;
    }
    if (selectedFiles.length === 0) {
      setImportError("请选择至少一个 PDF 或 DXF 文件");
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
        setBatchName("");
        setRemark("");
        loadProjectFiles(selectedProject.id);
        loadConversionRuns(selectedProject.id);
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
        refreshProjects();
      })
      .catch(() => setSplitError("生成图纸页预览失败，请稍后重试"));
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

  const handleRunCadPipeline = (batchId: number) => {
    if (!selectedProject) {
      return;
    }
    if (cadPipelineSteps.length === 0) {
      setCadPipelineError("请选择至少一个 CAD 批量处理步骤。");
      return;
    }
    const hasActiveConverter = converterSettings.some((item) => item.is_enabled);
    if (cadPipelineSteps.includes("convert_dwg") && dwgFileCount > 0 && !hasActiveConverter) {
      setCadPipelineError("尚未配置 DWG 转 DXF 工具，请先在 CAD 转换设置中配置。");
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
    runCadPipeline(batchId, payload)
      .then((result) => {
        setCadPipelineResult(result);
        setCadPipelineElapsed(result.summary.duration_seconds);
        setCadPipelineError("");
        loadProjectFiles(selectedProject.id);
        loadProjectSheets(selectedProject.id);
        loadConversionRuns(selectedProject.id);
        refreshProjects();
      })
      .catch((error) => setCadPipelineError(formatApiError(error, "CAD 批量处理失败")))
      .finally(() => {
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
      .catch(() => setTitleCropError("生成标题栏裁剪图失败，请稍后重试"));
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
      })
      .catch(() => setTitleCropError("批量生成标题栏裁剪图失败，请稍后重试"));
  };

  const handleExtractSheetText = (sheetId: number) => {
    extractSheetText(sheetId)
      .then((result) => {
        setRecognitionError("");
        setRecognitionResult(singleRecognitionAsBatch(result, latestBatchId ?? 0));
      })
      .catch(() => setRecognitionError("PDF 文本提取失败，请稍后重试"));
  };

  const handleOcrSheetTitle = (sheetId: number) => {
    ocrSheetTitle(sheetId)
      .then((result) => {
        setRecognitionError("");
        setRecognitionResult(singleRecognitionAsBatch(result, latestBatchId ?? 0));
      })
      .catch(() => setRecognitionError("标题栏 OCR 失败，请确认已生成标题栏裁剪图"));
  };

  const handleExtractBatchText = (batchId: number) => {
    extractBatchText(batchId)
      .then((result) => {
        setRecognitionResult(result);
        setRecognitionError("");
      })
      .catch(() => setRecognitionError("批量 PDF 文本提取失败，请稍后重试"));
  };

  const handleOcrBatchTitles = (batchId: number) => {
    ocrBatchTitles(batchId)
      .then((result) => {
        setRecognitionResult(result);
        setRecognitionError("");
      })
      .catch(() => setRecognitionError("批量标题栏 OCR 失败，请确认已生成标题栏裁剪图"));
  };

  const handleLoadRuns = (sheetId: number) => {
    listRecognitionRuns(sheetId)
      .then((runs) => {
        setRecognitionRuns(runs);
        setRunsSheetId(sheetId);
        setRecognitionError("");
      })
      .catch(() => setRecognitionError("识别运行记录加载失败"));
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
      })
      .catch((error) => setCandidateError(formatApiError(error, "候选值生成失败。DXF 请先解析 DXF，再生成候选值。PDF 请先完成文本提取或 OCR 原始结果")))
      .finally(() => setBusyAction(""));
  };

  const handleGenerateBatchCandidates = (batchId: number) => {
    generateBatchCandidates(batchId)
      .then((result) => {
        setCandidateResult(result);
        setCandidateError("");
      })
      .catch(() => setCandidateError("批量生成候选值失败"));
  };

  const handleLoadCandidates = (sheetId: number) => {
    listSheetCandidates(sheetId)
      .then((data) => {
        setCandidates(data);
        setCandidatesSheetId(sheetId);
        setCandidateError("");
      })
      .catch(() => setCandidateError("候选值加载失败"));
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
        refreshProjects();
      })
      .catch(() => setFusionError("批量生成推荐字段失败"));
  };

  const handleLoadFieldValues = (sheetId: number) => {
    Promise.all([listSheetFieldValues(sheetId), listSheetEvidence(sheetId)])
      .then(([values, evidence]) => {
        setFieldValues(values);
        setFieldEvidence(evidence);
        setFieldValuesSheetId(sheetId);
        setFusionError("");
      })
      .catch(() => setFusionError("推荐字段或证据加载失败"));
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
      .catch(() => setFusionError("图纸详情加载失败"));
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
      .catch(() => setReviewError("采用候选值失败"));
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
      .catch(() => setReviewError("存在阻断问题，暂不能确认"));
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
      .catch(() => setReviewError("问题状态更新失败"));
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
      setReviewError(source === "manual" ? "请先勾选要批量确认的图纸" : "当前筛选结果为空");
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
      })
      .catch(() => setReviewError("批量确认失败"));
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
      .catch(() => setExportError("导出前检查失败"));
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
        listExports(selectedProject.id).then(setExportRecords);
      })
      .catch(() => setExportError("导出失败：项目无图纸、导出目录不可写或 Excel 文件写入失败"));
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
    (file) => file.source_format === "dxf" && file.status !== "cad_pending"
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
  const projectNotice = (() => {
    if (projectFiles.length === 0 && sheetPage.total === 0) {
      return "当前项目还没有导入图纸。";
    }
    if (projectFiles.length > 0 && sheetPage.total === 0 && unsplitFileCount > 0) {
      return "已有 PDF 文件，尚未生成图纸页预览。";
    }
    if (sheets.some((sheet) => sheet.title_crop_status !== "success")) {
      return "部分图纸尚未生成标题栏裁剪图。";
    }
    if (sheets.length > 0 && !candidateResult) {
      return "部分图纸尚未生成候选值。";
    }
    if (sheets.length > 0 && recommendedCount < sheets.length) {
      return "部分图纸尚未生成推荐字段。";
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

              <div className="summary-grid">
                <Metric label="图纸总数" value={selectedProject.stats.sheet_count} />
                <Metric label="已识别" value={selectedProject.stats.recognized_count} />
                <Metric label="待校核" value={selectedProject.stats.need_review_count} />
                <Metric label="已确认" value={selectedProject.stats.confirmed_count} />
                <Metric label="识别失败" value={selectedProject.stats.failed_count || failedSheetCount} />
                <Metric label="问题数量" value={selectedProject.stats.issue_count} />
                <Metric label="Error" value={selectedProject.stats.error_issue_count} />
                <Metric label="Warning" value={selectedProject.stats.warning_issue_count} />
                <Metric label="已上传文件" value={projectFiles.length} />
                <Metric label="PDF 文件" value={pdfFileCount} />
                <Metric label="DXF 文件" value={dxfFileCount} />
                <Metric label="DWG 文件" value={dwgFileCount} />
                <Metric label="图纸页数量" value={sheets.length} />
                <Metric label="DXF 图纸页" value={dxfSheetCount} />
                <Metric label="DXF 已解析" value={dxfParsedCount} />
                <Metric label="DXF 解析失败" value={dxfFailedCount} />
                <Metric label="DXF 推荐字段" value={dxfRecommendedCount} />
                <Metric label="预处理完成" value={preprocessedCount} />
                <Metric label="标题栏裁剪" value={titleCroppedCount} />
                <Metric label="推荐字段" value={recommendedCount} />
                <Metric label="A/B/C/D" value={selectedProject.stats.trust_level_a_count + selectedProject.stats.trust_level_b_count + selectedProject.stats.trust_level_c_count + selectedProject.stats.trust_level_d_count} />
              </div>

              <p className="empty-guide">
                PDF 图纸台账识别流程内测版。当前 OCR 为内测占位能力，扫描 PDF 识别质量有限。
              </p>

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
                  <Metric label="推荐字段" value={dxfRecommendedCount} />
                  <Metric label="失败数量" value={failedSheetCount + pendingDwgFiles.filter((file) => file.convert_status === "failed").length} />
                </div>
                <div className="pipeline-options">
                  {([
                    "convert_dwg",
                    "prepare_dxf_sheet",
                    "parse_dxf",
                    "generate_candidates",
                    "fuse_fields"
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
                <button
                  type="button"
                  disabled={!latestBatchId || busyAction === `cad-pipeline-${latestBatchId}`}
                  onClick={() => latestBatchId && handleRunCadPipeline(latestBatchId)}
                >
                  {latestBatchId && busyAction === `cad-pipeline-${latestBatchId}` ? "批量处理中..." : "开始批量处理"}
                </button>
                {latestBatchId && busyAction === `cad-pipeline-${latestBatchId}` ? (
                  <div className="pipeline-running">
                    <strong>正在批量处理，请勿关闭页面</strong>
                    <span>当前步骤：{cadPipelineSteps.map(pipelineStepLabel).join(" → ")}</span>
                    <span>已完成步骤：同步执行中，完成后显示每一步结果</span>
                    <span>耗时：{formatDuration(cadPipelineElapsed)}</span>
                  </div>
                ) : null}
                {cadPipelineError ? <p className="form-error">{cadPipelineError}</p> : null}
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
                {converterError ? <p className="form-error">{converterError}</p> : null}
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
                    <span>当前支持 PDF、DXF 和 DWG 文件</span>
                  </div>
                  <p className="empty-state">
                    DWG 文件会先保存原始文件，不会直接解析；请配置本机转换工具后转换为 DXF。
                  </p>
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
                  {selectedFiles.length > 0 ? (
                    <div className="file-list">
                      {selectedFiles.map((file) => (
                        <div className="file-row" key={`${file.name}-${file.size}`}>
                          <span>{file.name}</span>
                          <span>{formatFileSize(file.size)}</span>
                          <span>{drawingFileLabel(file.name)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="empty-state">请选择一个或多个 PDF / DXF / DWG 文件。</p>
                  )}
                  {importError ? <p className="form-error">{importError}</p> : null}
                  <button type="submit">开始导入</button>
                </form>
              ) : null}

              {importResult ? (
                <div className="import-result">
                  <div className="section-title">
                    <h3>导入结果</h3>
                    <span>{importResult.file_count} 个文件</span>
                  </div>
                  <p>批次名称：{importResult.batch_name}</p>
                  <div className="file-list">
                    {importResult.files.map((file) => (
                      <div className="file-row" key={file.id}>
                        <span>{file.original_name}</span>
                        <span>{formatFileSize(file.file_size)}</span>
                        <span>{file.source_format.toUpperCase()}</span>
                        <span>{statusLabel(file.status)}</span>
                        <span>
                          {file.source_format === "dxf"
                            ? "DXF 文件已上传，尚未创建图纸页。"
                            : file.source_format === "dwg"
                              ? "DWG 已保存，请先执行转换为 DXF。"
                              : file.warnings.includes("duplicate_file")
                              ? "重复文件"
                              : "已导入"}
                        </span>
                        {file.source_format === "dxf" ? (
                          <button type="button" onClick={() => handlePrepareDxfSheet(file.id)}>
                            准备 DXF 图纸页
                          </button>
                        ) : null}
                        {file.source_format === "dwg" ? (
                          <button type="button" onClick={() => handleConvertDwgFile(file.id)}>
                            转换为 DXF
                          </button>
                        ) : null}
                        {file.source_format === "dxf" ? (
                          <button type="button" onClick={() => handleParseDxfFile(file.id)}>
                            解析 DXF
                          </button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                  {importResult.files.some((file) => file.source_format === "pdf") ? (
                    <>
                      <button type="button" onClick={() => handleSplitBatch(importResult.id)}>
                        生成图纸页预览
                      </button>
                      <button type="button" onClick={() => handleCropBatchTitles(importResult.id)}>
                        批量生成标题栏裁剪图
                      </button>
                    </>
                  ) : null}
                  {importResult.files.some((file) => file.source_format === "dxf") ? (
                    <button
                      type="button"
                      onClick={() => handlePrepareBatchDxfSheets(importResult.id)}
                    >
                      批量准备 DXF 图纸页
                    </button>
                  ) : null}
                  {importResult.files.some((file) => file.source_format === "dwg") ? (
                    <button type="button" onClick={() => handleConvertDwgBatch(importResult.id)}>
                      批量转换 DWG
                    </button>
                  ) : null}
                  {importResult.files.some((file) => file.source_format === "dxf") ? (
                    <button type="button" onClick={() => handleParseDxfBatch(importResult.id)}>
                      批量解析 DXF
                    </button>
                  ) : null}
                </div>
              ) : null}

              {splitError ? <p className="form-error">{splitError}</p> : null}
              {dxfPrepareError ? <p className="form-error">{dxfPrepareError}</p> : null}
              {cadParseError ? <p className="form-error">{cadParseError}</p> : null}
              {titleCropError ? <p className="form-error">{titleCropError}</p> : null}
              {recognitionError ? <p className="form-error">{recognitionError}</p> : null}
              {candidateError ? <p className="form-error">{candidateError}</p> : null}
              {fusionError ? <p className="form-error">{fusionError}</p> : null}

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
                  <p className="empty-state">没有符合条件的图纸。</p>
                ) : null}
                {sheets.length === 0 ? (
                  <p className="empty-state">
                    {projectFiles.length === 0 ? "当前项目还没有导入图纸。" : "暂无图纸页可显示。"}
                  </p>
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
                            <span className="thumb-placeholder small">DXF 暂无预览</span>
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
                          ) : null}
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
                    <p className="empty-state">暂无运行记录</p>
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
                    <p className="empty-state">暂无候选值</p>
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
                    <p className="empty-state">暂无推荐字段</p>
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
                  <p className="empty-state">暂无问题</p>
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

              {reviewSheet ? (
                <div className="review-workbench">
                  <div className="section-title">
                    <h3>校核工作台</h3>
                    <span>
                      {reviewSheet.original_file_name} 第 {reviewSheet.page_no} 页 / Ctrl+S 保存 / Ctrl+Enter 保存并确认
                    </span>
                  </div>
                  {reviewError ? <p className="form-error">{reviewError}</p> : null}
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
                        <p className="empty-state">部分图纸尚未生成推荐字段。</p>
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
                        <p className="empty-state">暂无审计日志</p>
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
                {exportError ? <p className="form-error">{exportError}</p> : null}
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
                  <div className="success-message">
                    <strong>Excel 台账已生成</strong>
                    <span>文件名：{exportResult.file_name}</span>
                    <span>图纸总台账：{exportResult.ledger_row_count} 行</span>
                    <span>问题清单：{exportResult.issue_row_count} 行</span>
                    {exportResult.warning_count > 0 ? (
                      <span>导出已完成，但存在未校核或低可信图纸，请在 Excel 中重点复核。</span>
                    ) : null}
                    <button type="button" onClick={() => downloadExport(exportResult.export_id)}>下载</button>
                  </div>
                ) : null}
                <div className="sheet-list">
                  <div className="section-title">
                    <h3>导出历史</h3>
                    <span>{exportRecords.length} 条</span>
                  </div>
                  {exportRecords.length === 0 ? (
                    <p className="empty-state">暂无导出记录</p>
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
            <div className="project-placeholder">
              <h2>选择或新建一个项目</h2>
              <p>项目会作为后续 PDF 图纸导入和台账识别的容器。</p>
            </div>
          )}
        </section>
      </section>

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
                <h4>整页预览</h4>
                {previewSheet.preview_path ? (
                  <img
                    src={`/api/sheets/${previewSheet.id}/preview`}
                    alt={`${previewSheet.original_file_name} 第 ${previewSheet.page_no} 页预览`}
                  />
                ) : (
                  <p className="empty-state">图片不可用或文件缺失。</p>
                )}
              </div>
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
                    <p className="empty-state">部分图纸尚未生成标题栏裁剪图。</p>
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
            </div>
            {detailSheet?.id === previewSheet.id ? (
              <div className="detail-readonly">
                <section>
                  <h4>推荐字段</h4>
                  {fieldValues.length === 0 ? (
                    <p className="empty-state">暂无推荐字段</p>
                  ) : (
                    <FieldValueList values={fieldValues} evidence={fieldEvidence} />
                  )}
                </section>
                <section>
                  <h4>候选值</h4>
                  {candidates.length === 0 ? (
                    <p className="empty-state">暂无候选值</p>
                  ) : (
                    <CandidateGroups candidates={candidates} />
                  )}
                </section>
                <section>
                  <h4>识别运行记录</h4>
                  {recognitionRuns.length === 0 ? (
                    <p className="empty-state">暂无运行记录</p>
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
                    <p className="empty-state">暂无问题</p>
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
                  <p className="empty-state">CAD 可读取，但暂无可展示的文字或块属性。</p>
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
