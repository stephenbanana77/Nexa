import { tokens } from "../theme";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

/** Reusable empty state placeholder. */
export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      style={{
        padding: "60px 20px",
        textAlign: "center",
      }}
    >
      {icon && <div style={{ marginBottom: tokens.spacing.md }}>{icon}</div>}
      <p style={{ color: tokens.color.text.tertiary, margin: 0, fontSize: tokens.fontSize.md }}>
        {title}
      </p>
      {description && (
        <p
          style={{
            color: tokens.color.text.muted,
            marginTop: tokens.spacing.xs,
            fontSize: tokens.fontSize.base,
          }}
        >
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: tokens.spacing.lg }}>{action}</div>}
    </div>
  );
}
