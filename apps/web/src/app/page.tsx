import { headers } from "next/headers";

export const dynamic = "force-dynamic";

type Health = {
  status: string;
  db: string;
};

async function fetchHealth(): Promise<Health> {
  const requestHeaders = await headers();
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? "http";

  try {
    const response = await fetch(`${protocol}://${host}/api/v1/health`, {
      cache: "no-store",
    });
    const data = (await response.json()) as Health;
    return { status: data.status, db: data.db };
  } catch {
    return { status: "unreachable", db: "unknown" };
  }
}

export default async function HomePage() {
  const health = await fetchHealth();
  const healthy = health.status === "ok" && health.db === "ok";

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-950 text-slate-100">
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-8">
        <h1 className="text-3xl font-bold">Postly</h1>
        <p className="mt-1 text-sm text-slate-400">
          Local problems, community answers.
        </p>

        <dl className="mt-8 space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-slate-400">API</dt>
            <dd className={healthy ? "text-emerald-400" : "text-red-400"}>
              {health.status}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-slate-400">Database</dt>
            <dd
              className={
                health.db === "ok" ? "text-emerald-400" : "text-red-400"
              }
            >
              {health.db}
            </dd>
          </div>
        </dl>
      </div>
    </main>
  );
}
