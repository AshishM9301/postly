import {
  CircleHelp,
  Construction,
  Droplets,
  Lightbulb,
  Route,
  Trash2,
  Volume2,
  Waves,
  Zap,
  type LucideIcon,
} from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  pothole: Construction,
  water: Droplets,
  garbage: Trash2,
  electricity: Zap,
  roads: Route,
  streetlight: Lightbulb,
  noise: Volume2,
  drainage: Waves,
  other: CircleHelp,
};

export function CategoryIcon({
  slug,
  className,
}: {
  slug: string;
  className?: string;
}) {
  const Icon = ICONS[slug] ?? CircleHelp;
  return <Icon className={className} aria-hidden="true" />;
}
