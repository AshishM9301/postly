import { Badge } from "~/components/ui/badge";
import type { PostStatus } from "~/lib/api/endpoints";

const LABELS: Record<PostStatus, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  SOLVED: "Solved",
  CLOSED: "Closed",
};

const STYLES: Record<PostStatus, string> = {
  OPEN: "bg-amber-100 text-amber-900 dark:bg-amber-500/15 dark:text-amber-300",
  IN_PROGRESS: "bg-blue-100 text-blue-900 dark:bg-blue-500/15 dark:text-blue-300",
  SOLVED:
    "bg-emerald-100 text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-300",
  CLOSED: "bg-slate-100 text-slate-700 dark:bg-slate-500/15 dark:text-slate-300",
};

export function StatusBadge({ status }: { status: PostStatus }) {
  return (
    <Badge variant="outline" className={`border-transparent ${STYLES[status]}`}>
      {LABELS[status]}
    </Badge>
  );
}
