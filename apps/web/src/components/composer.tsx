"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Loader2, X } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { AreaPicker } from "~/components/area-picker";
import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Progress, ProgressLabel } from "~/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Textarea } from "~/components/ui/textarea";
import {
  createPost,
  getCategories,
  uploadMedia,
  type AreaOut,
} from "~/lib/api/endpoints";
import type { Coordinates } from "~/lib/geo";
import { createGhostPostIdentity } from "~/lib/identity";
import { deletePostKey } from "~/lib/ghost";

type Stage = "idle" | "posting" | "uploading";

export function ComposerDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [area, setArea] = useState<AreaOut | null>(null);
  const [coords, setCoords] = useState<Coordinates | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
    staleTime: 5 * 60 * 1000,
    enabled: open,
  });

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function reset() {
    setTitle("");
    setBody("");
    setCategoryId("");
    setArea(null);
    setCoords(null);
    setFile(null);
    setError(null);
    setStage("idle");
    if (fileInput.current) {
      fileInput.current.value = "";
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!title.trim() || !body.trim()) {
      setError("Add a title and a description of the problem.");
      return;
    }
    if (!area) {
      setError("Choose your area with a PIN, a name, or your location.");
      return;
    }
    if (!categoryId) {
      setError("Pick a category.");
      return;
    }

    const postId = crypto.randomUUID();
    let created = false;
    setStage("posting");

    try {
      const identity = await createGhostPostIdentity(postId);
      await createPost({
        id: postId,
        title: title.trim(),
        body: body.trim(),
        area_id: area.id,
        category_id: categoryId,
        alias: identity.alias,
        owner_key: identity.ownerKey,
        status: "OPEN",
        ...(coords ? { lat: coords.lat, lng: coords.lng } : {}),
      });
      created = true;

      if (file) {
        setStage("uploading");
        try {
          await uploadMedia(file, postId, identity.ownerKey);
        } catch (uploadError) {
          toast.error(
            `Post created, but the photo failed: ${
              uploadError instanceof Error ? uploadError.message : "unknown error"
            }`,
          );
        }
      }

      await queryClient.invalidateQueries({ queryKey: ["feed"] });
      await queryClient.invalidateQueries({ queryKey: ["own-post-ids"] });
      toast.success("Problem reported");
      reset();
      onOpenChange(false);
    } catch (submitError) {
      if (!created) {
        try {
          await deletePostKey(postId);
        } catch {
          // Best-effort cleanup; the original error is the one to show.
        }
      }
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Could not create the post.",
      );
    } finally {
      setStage("idle");
    }
  }

  const busy = stage !== "idle";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Report a problem</DialogTitle>
          <DialogDescription>
            Posting as your local alias. No account needed.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={(event) => void onSubmit(event)}>
          <div className="space-y-1.5">
            <Label htmlFor="post-title">Title</Label>
            <Input
              id="post-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Deep pothole near the gate"
              maxLength={200}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="post-body">What is happening?</Label>
            <Textarea
              id="post-body"
              value={body}
              onChange={(event) => setBody(event.target.value)}
              placeholder="Three bikes have crashed here this week."
              maxLength={10_000}
              rows={4}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="post-category">Category</Label>
            <Select
              value={categoryId.length > 0 ? categoryId : null}
              onValueChange={(value) => setCategoryId(value ?? "")}
            >
              <SelectTrigger id="post-category" className="w-full">
                <SelectValue placeholder="Pick a category" />
              </SelectTrigger>
              <SelectContent>
                {(categories.data ?? []).map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <AreaPicker
            value={area}
            onChange={(nextArea, nextCoords) => {
              setArea(nextArea);
              setCoords(nextCoords);
            }}
          />

          <div className="space-y-1.5">
            <Label htmlFor="post-photo">Photo or short video (optional)</Label>
            <div className="flex items-center gap-2">
              <Input
                ref={fileInput}
                id="post-photo"
                type="file"
                accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              {file ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label="Remove photo"
                  onClick={() => setFile(null)}
                >
                  <X className="size-4" />
                </Button>
              ) : null}
            </div>
            {previewUrl && file?.type.startsWith("image/") ? (
              <div
                role="img"
                aria-label="Selected photo preview"
                className="h-40 w-full rounded-lg border bg-cover bg-center"
                style={{ backgroundImage: `url(${previewUrl})` }}
              />
            ) : null}
            {file && !file.type.startsWith("image/") ? (
              <p className="text-xs text-muted-foreground">
                {file.name} · video will upload after the post is created.
              </p>
            ) : null}
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <ImagePlus className="size-3" />
              JPEG, PNG, WebP, MP4 or MOV · up to 20 MB
            </p>
          </div>

          {busy ? (
            <Progress value={stage === "uploading" ? 75 : 35}>
              <ProgressLabel>
                {stage === "posting" ? "Creating your post…" : "Uploading photo…"}
              </ProgressLabel>
            </Progress>
          ) : null}

          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : null}
              {busy ? "Posting…" : "Post problem"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
