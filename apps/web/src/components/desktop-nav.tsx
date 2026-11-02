"use client";

import { RailBrand } from "~/components/rail-brand";
import { RailFooter } from "~/components/rail-footer";
import { RailNav } from "~/components/rail-nav";

export function DesktopNav() {
  return (
    <aside
      aria-label="Primary"
      className="group/nav fixed inset-y-0 left-0 z-50 hidden w-16 flex-col border-r bg-background transition-[width] duration-200 ease-out hover:w-60 focus-within:w-60 md:flex"
    >
      <RailBrand />
      <RailNav />
      <RailFooter />
    </aside>
  );
}
