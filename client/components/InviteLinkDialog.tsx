"use client";

import { Copy, MailCheck, MailWarning } from "lucide-react";
import { toast } from "sonner";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { copyText } from "@/lib/env";

export function InviteLinkDialog({
  open,
  onOpenChange,
  inviteUrl,
  emailSent,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  inviteUrl: string;
  emailSent: boolean;
}) {
  async function copy() {
    try {
      await copyText(inviteUrl);
      toast.success("Invite link copied");
    } catch {
      toast.error("Could not copy the link");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite ready</DialogTitle>
          <DialogDescription>
            {emailSent
              ? "The invitation email has been sent. You can also copy the link below."
              : "Email is not configured, so no message was sent. Share this link with the invitee."}
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div className={`sc-notice ${emailSent ? "sc-notice--lime" : "sc-notice--warn"}`}>
            {emailSent ? <MailCheck size={17} /> : <MailWarning size={17} />}
            <span>{emailSent ? "Email accepted by Resend." : "Copy and send this link manually."}</span>
          </div>
          <div className="sc-copyrow">
            <input className="sc-input sc-mono" value={inviteUrl} readOnly aria-label="Invite URL" />
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => void copy()}>
              <Copy size={15} /> Copy
            </button>
          </div>
        </DialogBody>
        <DialogFooter>
          <button type="button" className="sc-btn sc-btn--primary" onClick={() => onOpenChange(false)}>
            Done
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
