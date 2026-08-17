"use client";

import { useEffect, type RefObject } from "react";

function nestedScrollerCanConsume(
  target: EventTarget | null,
  root: HTMLElement,
  delta: number
) {
  let element = target instanceof HTMLElement ? target : null;
  while (element && element !== root) {
    if (element.hasAttribute("data-dashboard-wheel-native")) return true;
    const style = window.getComputedStyle(element);
    const scrollable = /(auto|scroll)/.test(style.overflowY);
    if (scrollable && element.scrollHeight > element.clientHeight) {
      if (delta < 0 && element.scrollTop > 0) return true;
      if (delta > 0 && element.scrollTop + element.clientHeight < element.scrollHeight) {
        return true;
      }
    }
    element = element.parentElement;
  }
  return false;
}

export function useDashboardInertialScroll(
  containerRef: RefObject<HTMLDivElement | null>,
  enabled: boolean
) {
  useEffect(() => {
    const container = containerRef.current;
    const finePointer = window.matchMedia("(pointer: fine)");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!enabled || !container || !finePointer.matches || reducedMotion.matches) return;

    let current = container.scrollTop;
    let target = current;
    let velocity = 0;
    let frame: number | null = null;
    let snapTimer: number | null = null;
    let animating = false;

    const maximumScroll = () => Math.max(0, container.scrollHeight - container.clientHeight);
    const clamp = (value: number) => Math.max(0, Math.min(maximumScroll(), value));

    const settleToSection = () => {
      snapTimer = null;
      const sectionHeight = container.clientHeight;
      if (sectionHeight <= 0) return;
      const projected = target + velocity * 10;
      target = clamp(Math.round(projected / sectionHeight) * sectionHeight);
      requestFrame();
    };

    const animate = () => {
      frame = null;
      const attraction = (target - current) * 0.035;
      velocity = (velocity + attraction) * 0.8;
      current = clamp(current + velocity);
      container.scrollTop = current;

      const settled = Math.abs(target - current) < 0.35 && Math.abs(velocity) < 0.12;
      if (settled) {
        current = target;
        velocity = 0;
        container.scrollTop = target;
        animating = false;
        container.classList.remove("dashboard-inertia-active");
        return;
      }
      frame = requestAnimationFrame(animate);
    };

    const requestFrame = () => {
      if (frame === null) {
        container.classList.add("dashboard-inertia-active");
        animating = true;
        frame = requestAnimationFrame(animate);
      }
    };

    const handleWheel = (event: WheelEvent) => {
      if (event.ctrlKey || nestedScrollerCanConsume(event.target, container, event.deltaY)) {
        return;
      }

      const modeScale = event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? 16
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? container.clientHeight
          : 1;
      const delta = event.deltaY * modeScale;
      if (Math.abs(delta) < 0.01) return;

      event.preventDefault();
      current = frame === null ? container.scrollTop : current;
      target = clamp(target + delta);
      velocity += delta * 0.018;
      requestFrame();

      if (snapTimer !== null) window.clearTimeout(snapTimer);
      snapTimer = window.setTimeout(settleToSection, 140);
    };

    const syncNativePosition = () => {
      if (!animating) {
        current = container.scrollTop;
        target = current;
      }
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    container.addEventListener("scroll", syncNativePosition, { passive: true });
    return () => {
      container.removeEventListener("wheel", handleWheel);
      container.removeEventListener("scroll", syncNativePosition);
      if (frame !== null) cancelAnimationFrame(frame);
      if (snapTimer !== null) window.clearTimeout(snapTimer);
      container.classList.remove("dashboard-inertia-active");
    };
  }, [containerRef, enabled]);
}
