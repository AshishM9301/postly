"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2, LocateFixed, MapPin, Search, X } from "lucide-react";
import { useState } from "react";

import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { detectArea, searchAreas, type AreaOut } from "~/lib/api/endpoints";
import { getBrowserLocation, type Coordinates } from "~/lib/geo";
import { useDebouncedValue } from "~/lib/use-debounced-value";

export function AreaPicker({
  value,
  onChange,
}: {
  value: AreaOut | null;
  onChange: (area: AreaOut | null, coords: Coordinates | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const debounced = useDebouncedValue(query.trim(), 250);

  const search = useQuery({
    queryKey: ["areas", debounced],
    queryFn: () => searchAreas(debounced),
    enabled: debounced.length > 0,
    staleTime: 60_000,
  });

  async function locateWithGps() {
    setGeoError(null);
    setLocating(true);
    try {
      const coords = await getBrowserLocation();
      const area = await detectArea(coords.lat, coords.lng);
      onChange(area, coords);
      setQuery("");
    } catch (error) {
      setGeoError(error instanceof Error ? error.message : "Location unavailable.");
    } finally {
      setLocating(false);
    }
  }

  if (value) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-lg border p-3">
        <div className="flex min-w-0 items-center gap-2">
          <MapPin className="size-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{value.name}</p>
            <p className="text-xs text-muted-foreground">
              PIN {value.pincode} · {value.district}
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Change area"
          onClick={() => onChange(null, null)}
        >
          <X className="size-4" />
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label htmlFor="area-search">Area</Label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="area-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="PIN code or neighbourhood, e.g. 110019"
            autoComplete="off"
            className="pl-8"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => void locateWithGps()}
          disabled={locating}
        >
          {locating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <LocateFixed className="size-4" />
          )}
          <span className="hidden sm:inline">Use location</span>
          <span className="sm:hidden">GPS</span>
        </Button>
      </div>

      {geoError ? (
        <p className="text-xs text-destructive">{geoError}</p>
      ) : null}

      {debounced.length > 0 ? (
        <div className="rounded-lg border">
          {search.isPending ? (
            <p className="flex items-center gap-2 p-3 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Searching areas…
            </p>
          ) : search.data && search.data.length > 0 ? (
            <ul className="divide-y">
              {search.data.map((area) => (
                <li key={area.id}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-muted"
                    onClick={() => {
                      onChange(area, null);
                      setQuery("");
                    }}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">
                        {area.name}
                      </span>
                      <span className="block text-xs text-muted-foreground">
                        {area.district}
                      </span>
                    </span>
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">
                      {area.pincode}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="p-3 text-sm text-muted-foreground">
              No areas found for “{debounced}”.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
