import { APP_VERSION } from "../constants";
import type { HealthResponse } from "../types";
import { StatusItem } from "./StatusItem";

interface AppHeaderProps {
  health: HealthResponse | null;
  healthError: boolean;
}

export function AppHeader({ health, healthError }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div>
        <p className="eyebrow">个人本地图纸台账工具</p>
        <h1>工程图纸智能台账识别系统</h1>
        <p className="hero-note">
          当前版本：{health?.version ?? APP_VERSION}。数据保存在 app_data 目录。
        </p>
      </div>
      {healthError ? (
        <div className="connection-error compact">
          <strong>后端未连接</strong>
          <span>后端未连接或服务未启动。请确认 start.bat 窗口仍在运行，再刷新页面。</span>
        </div>
      ) : (
        <div className="health-strip">
          <StatusItem label="后端状态" value={health?.status ?? "检查中"} />
          <StatusItem label="版本号" value={health?.version ?? "检查中"} />
          <StatusItem label="数据库状态" value={health?.database ?? "检查中"} />
          <StatusItem label="数据目录状态" value={health?.storage ?? "检查中"} />
        </div>
      )}
    </header>
  );
}
