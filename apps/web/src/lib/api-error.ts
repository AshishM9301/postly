import { ApiError } from "~/lib/api/client";

/** Show the API's machine code next to its message (e.g. `invalid_secret`). */
export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code ? `${error.code}: ${error.message}` : error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}
