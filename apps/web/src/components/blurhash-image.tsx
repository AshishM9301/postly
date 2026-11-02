"use client";

import { decode } from "blurhash";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { Skeleton } from "~/components/ui/skeleton";

export function BlurhashImage({
  src,
  blurHash,
  alt,
  className,
}: {
  src: string | null;
  blurHash: string | null;
  alt: string;
  className?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
    const canvas = canvasRef.current;
    if (!blurHash || !canvas) {
      return;
    }
    try {
      const pixels = decode(blurHash, 32, 32);
      const context = canvas.getContext("2d");
      if (!context) {
        return;
      }
      const imageData = context.createImageData(32, 32);
      imageData.data.set(pixels);
      context.putImageData(imageData, 0, 0);
    } catch {
      // A malformed hash just falls back to the skeleton.
    }
  }, [blurHash, src]);

  return (
    <div
      className={`relative overflow-hidden bg-muted ${className ?? ""}`}
      data-loaded={loaded}
    >
      {!loaded && blurHash ? (
        <canvas
          ref={canvasRef}
          width={32}
          height={32}
          aria-hidden="true"
          className="absolute inset-0 h-full w-full scale-110 blur-[2px]"
        />
      ) : null}
      {!loaded && !blurHash ? (
        <Skeleton className="absolute inset-0 h-full w-full rounded-none" />
      ) : null}
      {src ? (
        <Image
          src={src}
          alt={alt}
          fill
          unoptimized
          sizes="(max-width: 640px) 100vw, 640px"
          onLoad={() => setLoaded(true)}
          className={`relative object-cover transition-opacity duration-300 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
        />
      ) : null}
    </div>
  );
}
