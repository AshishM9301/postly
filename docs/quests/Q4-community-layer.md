# Q4 · Community layer

**Goal:** the app feels like a community: problems get resolved, blame gets debated, people follow each
other and their areas, and they hear about replies.

**Status:** not started (blocked by Q2)

**Done when**
- A post moves `OPEN → IN_PROGRESS → SOLVED` and the feed shows the status badge.
- The blame target can be voted on, and the community agrees/disagrees in the thread.
- A signed-in user can follow another user and an area, and the For You feed reflects both.
- A reply to your post creates a notification and a Web Push message.
- Ward-level areas are available (Delhi 70 wards) as an alternative to PIN codes.

**Planned tasks**

| ID | Task | Status |
|---|---|---|
| T-050 | Post status workflow + blame target + blame votes | planned |
| T-051 | Public profiles + user posts + follows | planned |
| T-052 | In-app notifications + Web Push (VAPID) | planned |
| T-053 | Ward-level areas (OSM admin boundaries + point-in-polygon) | planned |
| T-054 | Search + share links + Open Graph images | planned |

**Notes**
- Ward-level areas need OSM administrative relations and a polygon storage decision (GeoJSON vs PostGIS).
