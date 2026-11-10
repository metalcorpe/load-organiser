// Voluntary support link and the running costs it is meant to cover (#162).
// Owner decision 2026-11-09: Ko-fi; costs shown from the start. Update RUNNING_COSTS when a
// paid service starts or its price changes; nothing checks this automatically.

export const SUPPORT_URL = "https://ko-fi.com/tavaninja";

export interface RunningCost {
  item: string;
  /** Euros per month, as billed. */
  monthlyEur: number;
  since: string;
}

export const RUNNING_COSTS: readonly RunningCost[] = [];
