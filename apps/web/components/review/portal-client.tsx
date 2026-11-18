"use client";
import dynamic from "next/dynamic";
import { vi } from "@/messages/vi";

/** The portal reads its token from the address bar, so it renders in the browser only. */
export const ReviewPortal = dynamic(
  () => import("./portal-page").then((m) => m.ReviewPortalPage),
  {
    ssr: false,
    loading: () => <p className="en-muted">{vi.english.loading}</p>,
  },
);
