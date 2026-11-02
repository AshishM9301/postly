import { getSessionToken } from "../session.ts";
import type { paths } from "./types";

export type HealthData =
  paths["/api/v1/health"]["get"]["responses"][200]["content"]["application/json"];

export type ApiMeta = {
  cursor?: string;
  has_more?: boolean;
  [key: string]: unknown;
};

export type ApiEnvelope<T> = {
  data: T;
  meta?: ApiMeta;
};

export type ApiErrorPayload = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type ApiErrorEnvelope = {
  error: ApiErrorPayload;
};

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type QueryValue = string | number | boolean | null | undefined;

export type ApiRequestOptions = {
  method?: HttpMethod;
  query?: Record<string, QueryValue>;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

export type TokenGetter = () => string | null | Promise<string | null>;

/**
 * The transport seam. Keeping it injectable makes the client testable and keeps
 * `fetch` callable from exactly one place in the app.
 */
export type FetchLike = (
  input: string,
  init: RequestInit,
) => Promise<Response>;

export type ApiClientOptions = {
  baseUrl?: string;
  getToken?: TokenGetter;
  fetchImpl?: FetchLike;
};

export const DEFAULT_BASE_URL = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    payload: ApiErrorPayload,
    options?: { cause?: unknown },
  ) {
    super(payload.message, options);
    this.name = "ApiError";
    this.status = status;
    this.code = payload.code;
    this.details = payload.details ?? {};
  }

  static fromResponse(status: number, payload: unknown): ApiError {
    if (isApiErrorEnvelope(payload)) {
      return new ApiError(status, payload.error);
    }

    return new ApiError(status, {
      code: "internal_error",
      message: `Request failed with HTTP ${status}.`,
    });
  }
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }

  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string"
  );
}

function isApiEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    "data" in value &&
    !("error" in value)
  );
}

function isHealthData(value: unknown): value is HealthData {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    (record.status === "ok" || record.status === "degraded") &&
    (record.db === "ok" || record.db === "down")
  );
}

function joinUrl(baseUrl: string, path: string): string {
  const base = baseUrl.replace(/\/+$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${base}${suffix}`;
}

function withQuery(
  url: string,
  query?: Record<string, QueryValue>,
): string {
  if (!query) {
    return url;
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) {
      continue;
    }
    params.set(key, String(value));
  }

  const serialized = params.toString();
  return serialized.length > 0 ? `${url}?${serialized}` : url;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly getToken?: TokenGetter;
  private readonly fetchImpl: FetchLike;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;
    this.getToken = options.getToken;
    this.fetchImpl = options.fetchImpl ?? ((input, init) => fetch(input, init));
  }

  async health(): Promise<HealthData> {
    const payload = await this.send("/health", { method: "GET" });

    if (!isHealthData(payload)) {
      throw new ApiError(0, {
        code: "invalid_response",
        message: "GET /health returned an unexpected payload.",
      });
    }

    return payload;
  }

  async request<T>(
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<T> {
    return (await this.requestEnvelope<T>(path, options)).data;
  }

  /**
   * Like {@link request} but keeps the ``meta`` page info (feed cursors).
   */
  async requestEnvelope<T>(
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<ApiEnvelope<T>> {
    const payload = await this.send(path, options);

    if (!isApiEnvelope(payload)) {
      throw new ApiError(0, {
        code: "invalid_response",
        message: `Expected a { data, meta } envelope from ${path}.`,
      });
    }

    return payload as ApiEnvelope<T>;
  }

  /**
   * Send a request whose success carries no body (e.g. a 204 DELETE). Unlike
   * {@link request} this does not insist on a `{ data, meta }` envelope.
   */
  async requestVoid(
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<void> {
    await this.send(path, options);
  }

  private async send(
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<unknown> {
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");

    const token = await this.getToken?.();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    let body: BodyInit | undefined;
    if (options.body !== undefined) {
      if (options.body instanceof FormData) {
        body = options.body;
      } else {
        headers.set("Content-Type", "application/json");
        body = JSON.stringify(options.body);
      }
    }

    const url = withQuery(joinUrl(this.baseUrl, path), options.query);

    let response: Response;
    try {
      response = await this.fetchImpl(url, {
        method: options.method ?? "GET",
        headers,
        body,
        signal: options.signal,
      });
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      throw new ApiError(
        0,
        { code: "network_error", message: `Could not reach ${url}: ${reason}` },
        { cause: error },
      );
    }

    const text = await response.text();
    let payload: unknown;
    if (text.length > 0) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = undefined;
      }
    }

    if (!response.ok) {
      throw ApiError.fromResponse(response.status, payload);
    }

    return payload;
  }
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  return new ApiClient(options);
}

/** The main transport: carries the bearer token when a session is signed in. */
export const api = createApiClient({ getToken: getSessionToken });

/** Explicitly anonymous transport for owner-key ghost operations. */
export const ghostApi = createApiClient();

/** Authenticated transport used by `/me` and account deletion. */
export const sessionApi = api;
