import { AppHeader } from "~/components/app-header";
import { FeedBoard } from "~/components/feed-board";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto w-full max-w-xl px-4 py-4 pb-24">
        <FeedBoard />
      </main>
    </div>
  );
}
