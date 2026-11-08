"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  className,
  children,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="sc-overlay" />
      <DialogPrimitive.Content className={cn("sc-dialog", className)} {...props}>
        {children}
        <DialogPrimitive.Close className="sc-dialog-close" aria-label="Close">
          <X size={18} />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({ children }: { children: ReactNode }) {
  return <div className="sc-dialog-head">{children}</div>;
}

export function DialogTitle({
  className,
  ...props
}: ComponentProps<typeof DialogPrimitive.Title>) {
  return <DialogPrimitive.Title className={cn("sc-dialog-title", className)} {...props} />;
}

export function DialogDescription({
  className,
  ...props
}: ComponentProps<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description className={cn("sc-dialog-desc", className)} {...props} />
  );
}

export function DialogBody({ children }: { children: ReactNode }) {
  return <div className="sc-dialog-body">{children}</div>;
}

export function DialogFooter({ children }: { children: ReactNode }) {
  return <div className="sc-dialog-foot">{children}</div>;
}
