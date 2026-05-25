import { APP_TITLE } from "../constants";
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
        <p className="eyebrow">v1.1.1 快捷修复</p>
        <h1>{APP_TITLE}</h1>
        <p className="hero-note">
          当前为真实使用体验优化版，所有数据保存在 app_data 目录；备份 app_data 即可备份项目数据。
        </p>
      </div>
      {healthError ? (
        <div className="connection-error compact">
          <strong>后端未连接</strong>
          <span>后端未连接，请确认本地服务是否启动。</span>
        </div>
      ) : (
        <div className="health-strip">
          <StatusItem label="后端状态" value={health?.status ?? "检查中"} />
          <StatusItem label="版本号" value={health?.version ?? "检查中"} />
          <StatusItem label="数据库" value={health?.database ?? "检查中"} />
          <StatusItem label="存储" value={health?.storage ?? "检查中"} />
        </div>
      )}
    </header>
  );
}
