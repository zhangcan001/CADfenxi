import { APP_VERSION } from "../constants";

export function StatusItem({ label, value }: { label: string; value: string }) {
  const isOk = value === "ok" || value === APP_VERSION;

  return (
    <div className="status-item">
      <span>{label}</span>
      <strong className={isOk ? "ok" : ""}>{value}</strong>
    </div>
  );
}
