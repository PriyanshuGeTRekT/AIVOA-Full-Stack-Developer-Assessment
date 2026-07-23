// Small formatting helpers shared across components.

export function formatDate(iso) {
  if (!iso) return "-";
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function riskClass(level) {
  if (!level) return "neutral";
  return level.toLowerCase();
}
