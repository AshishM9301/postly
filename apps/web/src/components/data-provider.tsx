"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { DataPrivacyDialog } from "~/components/data-privacy-dialog";

type DataContextValue = {
  open: boolean;
  openDataPrivacy: () => void;
};

const DataContext = createContext<DataContextValue | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const openDataPrivacy = useCallback(() => setOpen(true), []);

  const value = useMemo(() => ({ open, openDataPrivacy }), [open, openDataPrivacy]);

  return (
    <DataContext.Provider value={value}>
      {children}
      <DataPrivacyDialog open={open} onOpenChange={setOpen} />
    </DataContext.Provider>
  );
}

export function useDataPrivacy(): DataContextValue {
  const context = useContext(DataContext);
  if (context === null) {
    throw new Error("useDataPrivacy must be used inside DataProvider");
  }
  return context;
}
