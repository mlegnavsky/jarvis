# Next sale readiness

After daily sale completion, show tomorrow's best configured contiguous positive-price window, using complete published Prague-day quarter-hour net prices after the sale fee. Display day/start/end/average and price-plan readiness. Missing/duplicate/invalid quarters mean waiting for complete prices; complete nonpositive data means no eligible window. Device readiness and available battery energy are rechecked only at actual start, never promised from prices.

Keep completed daily proof separate from the upcoming plan. Persist the upcoming price plan and promote it on its day only after matching its current quotes; never reopen a completed day. Preserve owner automatic intent and every native/sale guard. Existing configured duration stays unchanged. Use a separate next-plan paragraph in the existing controls card. This is a small extension of the existing planner and UI, requested directly by Martin.
