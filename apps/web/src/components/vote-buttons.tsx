"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowBigDown, ArrowBigUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { castVote, removeVote } from "~/lib/api/endpoints";
import { voterKeyFor } from "~/lib/identity";
import { getMyVote, setMyVote, type VoteValue } from "~/lib/votes-store";

export function VoteButtons({
  postId,
  initialUpvotes,
  initialDownvotes,
}: {
  postId: string;
  initialUpvotes: number;
  initialDownvotes: number;
}) {
  const [upvotes, setUpvotes] = useState(initialUpvotes);
  const [downvotes, setDownvotes] = useState(initialDownvotes);
  const [myVote, setMyVoteState] = useState<VoteValue | null>(null);
  const [mounted, setMounted] = useState(false);
  const previous = useRef({
    upvotes: initialUpvotes,
    downvotes: initialDownvotes,
    myVote: null as VoteValue | null,
  });

  useEffect(() => {
    setMyVoteState(getMyVote(postId));
    setMounted(true);
  }, [postId]);

  const mutation = useMutation({
    mutationFn: async (next: VoteValue | null) => {
      const voterKey = await voterKeyFor(postId);
      return next === null
        ? removeVote("POST", postId, voterKey)
        : castVote("POST", postId, next, voterKey);
    },
    onSuccess: (result) => {
      setUpvotes(result.upvote_count);
      setDownvotes(result.downvote_count);
      setMyVoteState(result.value);
      setMyVote(postId, result.value);
    },
    onError: (error) => {
      setUpvotes(previous.current.upvotes);
      setDownvotes(previous.current.downvotes);
      setMyVoteState(previous.current.myVote);
      setMyVote(postId, previous.current.myVote);
      toast.error(error instanceof Error ? error.message : "Could not save your vote");
    },
  });

  function click(value: VoteValue) {
    if (mutation.isPending) {
      return;
    }

    const next: VoteValue | null = myVote === value ? null : value;
    previous.current = { upvotes, downvotes, myVote };
    let nextUp = upvotes;
    let nextDown = downvotes;
    if (myVote === 1) nextUp -= 1;
    if (myVote === -1) nextDown -= 1;
    if (next === 1) nextUp += 1;
    if (next === -1) nextDown += 1;

    setUpvotes(Math.max(0, nextUp));
    setDownvotes(Math.max(0, nextDown));
    setMyVoteState(next);
    mutation.mutate(next);
  }

  return (
    <div className="flex items-center gap-1.5" aria-label="Vote on this post">
      <Button
        type="button"
        size="sm"
        variant={mounted && myVote === 1 ? "secondary" : "outline"}
        className={mounted && myVote === 1 ? "text-primary" : ""}
        aria-pressed={mounted && myVote === 1}
        aria-label="Upvote"
        disabled={mutation.isPending}
        onClick={() => click(1)}
      >
        <ArrowBigUp className="size-4" />
        <span className="tabular-nums">{upvotes}</span>
      </Button>
      <Button
        type="button"
        size="sm"
        variant={mounted && myVote === -1 ? "secondary" : "outline"}
        className={mounted && myVote === -1 ? "text-destructive" : ""}
        aria-pressed={mounted && myVote === -1}
        aria-label="Downvote"
        disabled={mutation.isPending}
        onClick={() => click(-1)}
      >
        <ArrowBigDown className="size-4" />
        <span className="tabular-nums">{downvotes}</span>
      </Button>
    </div>
  );
}
