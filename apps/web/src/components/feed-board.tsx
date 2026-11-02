"use client";

import { Loader2, LocateFixed, MapPin } from "lucide-react";

import { FEED_TABS, useFeedTab } from "~/components/feed-tab-provider";
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

export function FeedBoard() {
  const { tab, coords, geoState, geoError, selectTab, locate } = useFeedTab();

  function changeTab(value: string | number) {
    selectTab(String(value) as FeedTabName);
  }

  return (
    <Tabs value={tab} onValueChange={changeTab} className="w-full">
      <TabsList variant="line" className="grid w-full grid-cols-4">
        {FEED_TABS.map((item) => (
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
