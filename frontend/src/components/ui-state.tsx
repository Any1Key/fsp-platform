import type { ReactNode } from "react";

type StatePanelProps = {
  title: string;
  description?: string;
  className?: string;
  children?: ReactNode;
};

function classes(...names: Array<string | undefined>) {
  return names.filter(Boolean).join(" ");
}

export function LoadingState({ title, description, className }: StatePanelProps) {
  return (
    <div className={classes("uiState", "uiStateLoading", className)} data-ui-state="loading" role="status" aria-live="polite" aria-busy="true">
      <span className="uiStateMark" aria-hidden="true"><i /><i /><i /></span>
      <div>
        <strong>{title}</strong>
        {description && <p>{description}</p>}
      </div>
    </div>
  );
}

export function ErrorState({ title, description, className, children }: StatePanelProps) {
  return (
    <div className={classes("uiState", "uiStateError", className)} data-ui-state="error" role="alert">
      <span className="uiStateMark" aria-hidden="true">!</span>
      <div>
        <strong>{title}</strong>
        {description && <p>{description}</p>}
        {children && <div className="uiStateActions">{children}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ title, description, className, children }: StatePanelProps) {
  return (
    <div className={classes("uiState", "uiStateEmpty", className)} data-ui-state="empty">
      <span className="uiStateMark" aria-hidden="true">—</span>
      <div>
        <strong>{title}</strong>
        {description && <p>{description}</p>}
        {children && <div className="uiStateActions">{children}</div>}
      </div>
    </div>
  );
}

export function UnconfirmedGradeBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span className={classes("unconfirmedGradeBadge", compact ? "compact" : undefined)} data-ui-state="unconfirmed-grade">
      <i aria-hidden="true">!</i> {compact ? "NOT CONFIRMED" : "GRADE NOT CONFIRMED"}
    </span>
  );
}
