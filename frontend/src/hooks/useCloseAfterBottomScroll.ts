"use client";

import { useEffect, useRef, type TouchEvent, type UIEvent, type WheelEvent } from "react";

const BOTTOM_TOLERANCE = 4;
const GESTURE_LOCK_MS = 450;
const TOUCH_SCROLL_THRESHOLD = 24;

export function useCloseAfterBottomScroll(onClose: () => void) {
  const bottomScrollCount = useRef(0);
  const gestureLocked = useRef(false);
  const gestureTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const touchStartY = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (gestureTimer.current) clearTimeout(gestureTimer.current);
    },
    [],
  );

  const isAtBottom = (element: HTMLElement) =>
    element.scrollHeight - element.scrollTop - element.clientHeight <= BOTTOM_TOLERANCE;

  const countDownGesture = (element: HTMLElement) => {
    if (!isAtBottom(element) || gestureLocked.current) {
      if (!isAtBottom(element)) bottomScrollCount.current = 0;
      return;
    }

    gestureLocked.current = true;
    gestureTimer.current = setTimeout(() => {
      gestureLocked.current = false;
    }, GESTURE_LOCK_MS);

    bottomScrollCount.current += 1;
    if (bottomScrollCount.current >= 2) {
      bottomScrollCount.current = 0;
      onClose();
    }
  };

  const onWheel = (event: WheelEvent<HTMLElement>) => {
    if (event.deltaY < 0) {
      bottomScrollCount.current = 0;
      return;
    }
    if (event.deltaY > 0) countDownGesture(event.currentTarget);
  };

  const onTouchStart = (event: TouchEvent<HTMLElement>) => {
    touchStartY.current = event.touches[0]?.clientY ?? null;
  };

  const onTouchEnd = (event: TouchEvent<HTMLElement>) => {
    const startY = touchStartY.current;
    const endY = event.changedTouches[0]?.clientY;
    touchStartY.current = null;

    if (startY !== null && endY !== undefined && startY - endY >= TOUCH_SCROLL_THRESHOLD) {
      countDownGesture(event.currentTarget);
    } else if (startY !== null && endY !== undefined && endY - startY >= TOUCH_SCROLL_THRESHOLD) {
      bottomScrollCount.current = 0;
    }
  };

  const onScroll = (event: UIEvent<HTMLElement>) => {
    if (!isAtBottom(event.currentTarget)) bottomScrollCount.current = 0;
  };

  return { onWheel, onTouchStart, onTouchEnd, onScroll };
}