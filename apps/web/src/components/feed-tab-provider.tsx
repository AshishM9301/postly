"use client";

import { Clock, Flame, MapPin, Sparkles } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";

import type { FeedTabName } from "~/lib/api/endpoints";
import { getBrowserLocation, type Coordinates } from "~/lib/geo";

export type FeedTabDefinition = {
  value: FeedTabName;
  label: string;
  icon: ComponentType<{ className?: string }>;
};

export const FEED_TABS: FeedTabDefinition[] = [
  { value: "for-you", label: "For You", icon: Sparkles },
  { value: "trending", label: "Trending", icon: Flame },
  { value: "new", label: "New", icon: Clock },
  { value: "nearby", label: "Nearby", icon: MapPin },
];

type GeoState = "idle" | "locating" | "ready" | "error";

type FeedTabContextValue = {
  tab: FeedTabName;
  coords: Coordinates | null;
  geoState: GeoState;
  geoError: string | null;
  selectTab: (tab: FeedTabName) => void;
  locate: () => Promise<void>;
};

const FeedTabContext = createContext<FeedTabContextValue | null>(null);

export function FeedTabProvider({
  children,
  initialTab = "for-you",
}: {
  children: ReactNode;
  initialTab?: FeedTabName;
}) {
  const [tab, setTab] = useState<FeedTabName>(initialTab);
  const [coords, setCoords] = useState<Coordinates | null>(null);
  const [geoState, setGeoState] = useState<GeoState>("idle");
  const [geoError, setGeoError] = useState<string | null>(null);
  const autoLocated = useRef(false);

  const locate = useCallback(async () => {
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
  }, []);

  const selectTab = useCallback(
    (next: FeedTabName) => {
      setTab(next);
      if (
        next === "nearby" &&
        coords === null &&
        geoState !== "locating" &&
        !autoLocated.current
      ) {
        autoLocated.current = true;
        void locate();
      }
    },
    [coords, geoState, locate],
  );

  const value = useMemo(
    () => ({ tab, coords, geoState, geoError, selectTab, locate }),
    [tab, coords, geoState, geoError, selectTab, locate],
  );

  return (
    <FeedTabContext.Provider value={value}>{children}</FeedTabContext.Provider>
  );
}

export function useFeedTab(): FeedTabContextValue {
  const context = useContext(FeedTabContext);
  if (context === null) {
    throw new Error("useFeedTab must be used inside FeedTabProvider");
  }
  return context;
}
