from __future__ import annotations

import numpy as np
import pandas as pd


def triple_barrier_labels(
    prices: pd.DataFrame,
    horizon: int = 5,
    up_multiple: float = 2.0,
    down_multiple: float = 1.5,
) -> pd.DataFrame:
    """Label close-to-close entries by the first ATR barrier reached.

    Entries are assumed at the signal day's close. Subsequent daily OHLC bars
    are inspected in chronological order. A gap through a barrier is exited
    at the next session's open. If both barriers are touched intraday and the
    open did not already resolve the exit, the observation is marked
    ambiguous (NaN) rather than assigning a favourable ordering.

    If neither barrier is touched, the position exits at the horizon close and
    is labelled by the sign of its realised return (zero is negative).
    """
    required = {"open", "high", "low", "close", "atr"}
    missing = required.difference(prices.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if horizon < 1 or up_multiple <= 0 or down_multiple <= 0:
        raise ValueError("horizon and barrier multiples must be positive")

    data = prices.sort_index()
    rows: list[dict] = []
    n = len(data)
    for i in range(n):
        entry = float(data["close"].iloc[i])
        atr = float(data["atr"].iloc[i]) if pd.notna(data["atr"].iloc[i]) else np.nan
        result = {
            "target": np.nan,
            "exit_reason": "unresolved",
            "exit_date": pd.NaT,
            "exit_price": np.nan,
            "outcome_return": np.nan,
        }
        if not np.isfinite(entry) or entry <= 0 or not np.isfinite(atr) or atr <= 0:
            rows.append(result)
            continue
        if i + horizon >= n:
            rows.append(result)
            continue

        take_profit = entry + up_multiple * atr
        stop_loss = entry - down_multiple * atr
        resolved = False
        for j in range(i + 1, i + horizon + 1):
            bar = data.iloc[j]
            opn, high, low = (float(bar[k]) for k in ("open", "high", "low"))
            # Opening gaps are executable before the intraday range.
            if opn >= take_profit:
                exit_price, reason = opn, "target_gap"
            elif opn <= stop_loss:
                exit_price, reason = opn, "stop_gap"
            elif low <= stop_loss and high >= take_profit:
                result.update({"target": np.nan, "exit_reason": "ambiguous",
                               "exit_date": data.index[j]})
                resolved = True
                break
            elif high >= take_profit:
                exit_price, reason = take_profit, "target"
            elif low <= stop_loss:
                exit_price, reason = stop_loss, "stop"
            else:
                continue

            outcome_return = exit_price / entry - 1.0
            result.update({
                "target": int(reason.startswith("target")),
                "exit_reason": reason,
                "exit_date": data.index[j],
                "exit_price": exit_price,
                "outcome_return": outcome_return,
            })
            resolved = True
            break

        if not resolved:
            exit_price = float(data["close"].iloc[i + horizon])
            outcome_return = exit_price / entry - 1.0
            result.update({
                "target": int(outcome_return > 0),
                "exit_reason": "timeout",
                "exit_date": data.index[i + horizon],
                "exit_price": exit_price,
                "outcome_return": outcome_return,
            })
        rows.append(result)

    return pd.DataFrame(rows, index=data.index)
