import React from "react";

type CadPreviewViewerProps = {
  imageUrl: string | null;
  fileName: string;
  status: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  isGenerating?: boolean;
  onRegenerate: () => void;
};

const MIN_SCALE = 0.2;
const MAX_SCALE = 5;
const SCALE_STEP = 0.2;

function clampScale(value: number) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, value));
}

export function CadPreviewViewer({
  imageUrl,
  fileName,
  status,
  errorCode,
  errorMessage,
  isGenerating = false,
  onRegenerate
}: CadPreviewViewerProps) {
  const viewportRef = React.useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = React.useState(1);
  const [offset, setOffset] = React.useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = React.useState<{ x: number; y: number; originX: number; originY: number } | null>(null);
  const [imageLoaded, setImageLoaded] = React.useState(false);
  const [imageError, setImageError] = React.useState(false);
  const [naturalSize, setNaturalSize] = React.useState({ width: 0, height: 0 });
  const [imageVersion, setImageVersion] = React.useState(0);

  React.useEffect(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
    setImageLoaded(false);
    setImageError(false);
    setNaturalSize({ width: 0, height: 0 });
    setImageVersion((current) => current + 1);
  }, [imageUrl]);

  const displayImageUrl = React.useMemo(() => {
    if (!imageUrl) {
      return null;
    }
    const separator = imageUrl.includes("?") ? "&" : "?";
    return `${imageUrl}${separator}v=${imageVersion}`;
  }, [imageUrl, imageVersion]);

  const zoomTo = (nextScale: number) => {
    setScale(clampScale(nextScale));
  };

  const fitToWindow = () => {
    const viewport = viewportRef.current;
    if (!viewport || naturalSize.width <= 0 || naturalSize.height <= 0) {
      setScale(1);
      setOffset({ x: 0, y: 0 });
      return;
    }
    const nextScale = Math.min(
      (viewport.clientWidth - 32) / naturalSize.width,
      (viewport.clientHeight - 32) / naturalSize.height,
      1
    );
    setScale(clampScale(nextScale));
    setOffset({ x: 0, y: 0 });
  };

  const resetView = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    if (!imageUrl || imageError) {
      return;
    }
    event.preventDefault();
    const direction = event.deltaY > 0 ? -1 : 1;
    zoomTo(scale + direction * SCALE_STEP);
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!imageUrl || imageError || !imageLoaded) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragStart({ x: event.clientX, y: event.clientY, originX: offset.x, originY: offset.y });
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragStart) {
      return;
    }
    setOffset({
      x: dragStart.originX + event.clientX - dragStart.x,
      y: dragStart.originY + event.clientY - dragStart.y
    });
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragStart) {
      event.currentTarget.releasePointerCapture(event.pointerId);
      setDragStart(null);
    }
  };

  const downloadPreview = () => {
    if (!displayImageUrl) {
      return;
    }
    const link = document.createElement("a");
    link.href = displayImageUrl;
    link.download = `${fileName || "cad-preview"}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const hasPreview = Boolean(displayImageUrl && status === "success");
  const canUsePreview = hasPreview && imageLoaded && !imageError;
  const showFailure = status === "failed" || imageError;

  return (
    <section className="cad-preview-viewer">
      <div className="cad-preview-toolbar">
        <button type="button" className="ghost" onClick={() => zoomTo(scale + SCALE_STEP)} disabled={!canUsePreview}>
          放大
        </button>
        <button type="button" className="ghost" onClick={() => zoomTo(scale - SCALE_STEP)} disabled={!canUsePreview}>
          缩小
        </button>
        <button type="button" className="ghost" onClick={fitToWindow} disabled={!canUsePreview}>
          适应窗口
        </button>
        <button type="button" className="ghost" onClick={() => zoomTo(1)} disabled={!canUsePreview}>
          100%
        </button>
        <button type="button" className="ghost" onClick={resetView} disabled={!canUsePreview}>
          重置
        </button>
        <button type="button" onClick={onRegenerate} disabled={isGenerating}>
          {isGenerating ? "生成中..." : status === "failed" ? "重新生成" : "重新生成预览"}
        </button>
        <button type="button" className="ghost" onClick={downloadPreview} disabled={!canUsePreview}>
          下载预览图
        </button>
        <span className="cad-preview-scale">缩放：{Math.round(scale * 100)}%</span>
      </div>

      <div
        ref={viewportRef}
        className={`cad-preview-canvas${dragStart ? " is-dragging" : ""}`}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => setDragStart(null)}
      >
        {isGenerating ? (
          <p className="empty-state">正在生成 CAD 图形预览...</p>
        ) : showFailure ? (
          <div className="empty-state cad-preview-message">
            <strong>CAD 图形预览生成失败。</strong>
            <span>{imageError ? "CAD_PREVIEW_FILE_NOT_FOUND" : errorCode || "CAD_PREVIEW_RENDER_FAILED"}</span>
            <span>
              {imageError
                ? "预览图片无法加载，请重新生成预览。"
                : errorMessage || "请重新生成预览，或检查 DXF 文件是否可正常打开。"}
            </span>
            <span>预览失败不会影响图纸识别、校核或 Excel 导出。</span>
          </div>
        ) : hasPreview && displayImageUrl ? (
          <>
            {!imageLoaded ? <p className="empty-state cad-preview-loading">正在加载预览图...</p> : null}
            <img
              src={displayImageUrl}
              alt={`${fileName} CAD 图形预览`}
              draggable={false}
              onLoad={(event) => {
                const nextSize = {
                  width: event.currentTarget.naturalWidth,
                  height: event.currentTarget.naturalHeight
                };
                setNaturalSize(nextSize);
                setImageLoaded(true);
                window.requestAnimationFrame(() => {
                  const viewport = viewportRef.current;
                  if (!viewport || nextSize.width <= 0 || nextSize.height <= 0) {
                    return;
                  }
                  const nextScale = Math.min(
                    (viewport.clientWidth - 32) / nextSize.width,
                    (viewport.clientHeight - 32) / nextSize.height,
                    1
                  );
                  setScale(clampScale(nextScale));
                  setOffset({ x: 0, y: 0 });
                });
              }}
              onError={() => setImageError(true)}
              style={{
                transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`
              }}
            />
          </>
        ) : (
          <div className="empty-state cad-preview-message">
            <strong>CAD 图形预览尚未生成。</strong>
            <span>可生成轻量 PNG 预览后在此缩放、拖拽查看。</span>
          </div>
        )}
      </div>
    </section>
  );
}
