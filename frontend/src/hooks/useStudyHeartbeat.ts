"use client";

import { useEffect } from "react";

import api from "@/services/api";

const HEARTBEAT_INTERVAL_MS = 60_000;

export function useStudyHeartbeat(enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    let timer: number | null = null;

    const sendHeartbeat = () => {
      if (document.visibilityState !== "visible") return;

      // UTC+7 => +420. The backend uses this only to choose the user's local day.
      const timezoneOffsetMinutes = -new Date().getTimezoneOffset();
      void api
        .post("/users/heartbeat", null, {
          params: { timezone_offset_minutes: timezoneOffsetMinutes },
        })
        .catch(() => {
          // Heartbeat is analytics-only. Never interrupt the user's learning flow.
        });
    };

    const start = () => {
      if (timer !== null) return;
      sendHeartbeat();
      timer = window.setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
    };

    const stop = () => {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") start();
      else stop();
    };

    if (document.visibilityState === "visible") start();
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stop();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enabled]);
}
