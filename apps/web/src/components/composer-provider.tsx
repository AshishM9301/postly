"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ComposerDialog } from "~/components/composer";
import { ensureGhostIdentity } from "~/lib/identity";

type ComposerContextValue = {
  open: boolean;
  setOpen: (open: boolean) => void;
  openComposer: () => void;
};

const ComposerContext = createContext<ComposerContextValue | null>(null);

export function ComposerProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const handleOpenChange = useCallback((next: boolean) => {
    setOpen(next);
    if (next) {
      void ensureGhostIdentity().catch(() => undefined);
    }
  }, []);

  const openComposer = useCallback(() => {
    handleOpenChange(true);
  }, [handleOpenChange]);

  const value = useMemo(
    () => ({ open, setOpen: handleOpenChange, openComposer }),
    [open, handleOpenChange, openComposer],
  );

  return (
    <ComposerContext.Provider value={value}>
      {children}
      <ComposerDialog open={open} onOpenChange={handleOpenChange} />
    </ComposerContext.Provider>
  );
}

export function useComposer(): ComposerContextValue {
  const context = useContext(ComposerContext);
  if (context === null) {
    throw new Error("useComposer must be used inside ComposerProvider");
  }
  return context;
}
