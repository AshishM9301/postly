import { Badge } from "~/components/ui/badge";
import type { PostStatus } from "~/lib/api/endpoints";

const LABELS: Record<PostStatus, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  SOLVED: "Solved",
  CLOSED: "Closed",
};

const STYLES: Record<PostStatus, string> = {
  OPEN: "bg-primary/10 text-primary",
  IN_PROGRESS: "bg-muted text-foreground",
  SOLVED: "bg-foreground text-background",
  CLOSED: "bg-muted text-muted-foreground",
};

export function StatusBadge({ status }: { status: PostStatus }) {
  return (
    <Badge variant="outline" className={`border-transparent ${STYLES[status]}`}>
      {LABELS[status]}
    </Badge>
  );
}
