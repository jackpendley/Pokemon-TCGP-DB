"use client";

import { useState, useTransition } from "react";
import { Trash2 } from "lucide-react";

import { deleteDeck } from "@/app/decks/actions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/**
 * Deleting a deck is irreversible and there's no undo, so it asks first.
 * Rendered only for the owner — the action re-checks that server-side, and RLS
 * enforces it regardless.
 */
export function DeleteDeckButton({ id, name }: { id: string; name: string }) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={<Button variant="ghost" size="sm" />}
        aria-label={`Delete ${name}`}
      >
        <Trash2 className="size-4" />
        Delete
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Delete this deck?</DialogTitle>
          <DialogDescription>
            “{name}” will be removed permanently. This can’t be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter showCloseButton>
          <Button
            variant="destructive"
            disabled={pending}
            onClick={() => startTransition(() => deleteDeck(id))}
          >
            {pending ? "Deleting…" : "Delete deck"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
