/**
 * The default wiring between the ghost vault and the typed API client.
 *
 * `vault.ts` stays transport-agnostic (zero `fetch` calls); this module is the
 * one place that binds it to `client.ts`, which is the app's single fetch door.
 */

import { api, type ApiClient } from "./client.ts";
import type { GhostDeleteTransport } from "../ghost/vault.ts";

export function createGhostTransport(client: ApiClient): GhostDeleteTransport {
  return (postId, ownerKey) =>
    client.requestVoid(`/posts/${encodeURIComponent(postId)}`, {
      method: "DELETE",
      body: { owner_key: ownerKey },
    });
}

export const ghostTransport: GhostDeleteTransport = createGhostTransport(api);
