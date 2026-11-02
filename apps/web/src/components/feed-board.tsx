"use client";

import { Loader2, LocateFixed, MapPin } from "lucide-react";
import { useState } from "react";

import { FeedList } from "~/components/feed-list";
import { Button } from "~/components/ui/button";
import { Card, CardContent } from "~/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "~/components/ui/tabs";
import type { FeedTabName } from "~/lib/api/endpoints";
import { getBrowserLocation, type Coordinates } from "~/lib/geo";

const TABS: Array<{ value: FeedTabName; label: string }> = [
  { value: "for-you", label: "For You" },
  { value: "trending", label: "Trending" },
  { value: "new", label: "New" },
  { value: "nearby", label: "Nearby" },
];

type GeoState = "idle" | "locating" | "ready" | "error";

export function FeedBoard() {
  const [tab, setTab] = useState<FeedTabName>("for-you");
  const [coords, setCoords] = useState<Coordinates | null>(null);
  const [geoState, setGeoState] = useState<GeoState>("idle");
  const [geoError, setGeoError] = useState<string | null>(null);

  async function locate() {
    setGeoState("locating");
    setGeoError(null);
    try {
      const position = await getBrowserLocation();
      setCoords(position);
      setGeoState("ready");
    } catch (error) {
      setGeoError(error instanceof Error ? error.message : "Location unavailable.");
      setGeoState("error");
    }
  }

  function changeTab(value: string | number) {
    const next = String(value) as FeedTabName;
    setTab(next);
    if (next === "nearby" && coords === null && geoState !== "locating") {
      void locate();
    }
  }

  return (
    <Tabs value={tab} onValueChange={changeTab} className="w-full">
      <TabsList variant="line" className="grid w-full grid-cols-4">
        {TABS.map((item) => (
          <TabsTrigger key={item.value} value={item.value} className="px-1">
            {item.label}
          </TabsTrigger>
        ))}
      </TabsList>

      <TabsContent value="for-you" className="mt-3">
        <FeedList tab="for-you" />
      </TabsContent>
      <TabsContent value="trending" className="mt-3">
        <FeedList tab="trending" />
      </TabsContent>
      <TabsContent value="new" className="mt-3">
        <FeedList tab="new" />
      </TabsContent>
      <TabsContent value="nearby" className="mt-3">
        {coords ? (
          <FeedList tab="nearby" coords={coords} />
        ) : (
          <Card>
            <CardContent className="flex flex-col items-start gap-3 p-5">
              <div className="flex items-center gap-2">
                <MapPin className="size-5 text-muted-foreground" />
                <p className="font-medium">See what is around you</p>
              </div>
              <p className="text-sm text-muted-foreground">
                {geoState === "locating"
                  ? "Finding your location…"
                  : (geoError ??
                    "Allow location access to sort problems by distance.")}
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={geoState === "locating"}
                onClick={() => void locate()}
              >
                {geoState === "locating" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <LocateFixed className="size-4" />
                )}
                {geoState === "error" ? "Try location again" : "Use my location"}
              </Button>
            </CardContent>
          </Card>
        )}
      </TabsContent>
    </Tabs>
  );
}
