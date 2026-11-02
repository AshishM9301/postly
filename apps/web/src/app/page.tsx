import { AppShell } from "~/components/app-shell";
import { FeedBoard } from "~/components/feed-board";

export default function HomePage() {
  return (
    <AppShell>
      <FeedBoard />
    </AppShell>
  );
}
