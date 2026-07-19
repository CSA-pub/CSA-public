"""Load the CSA free sample and print a quick summary.

    python examples/load_sample.py

No dependencies beyond the Python standard library.
Full dataset: https://csa-public.pages.dev

CSA is data, not investment advice. Estimated catalyst dates routinely slip and
are graded by `confidence` — verify anything material against each row's source_url.
"""

import csv
import os
from collections import Counter

HERE = os.path.dirname(__file__)
CAL = os.path.join(HERE, "..", "samples", "catalyst_calendar_sample.csv")


def main() -> None:
    with open(CAL, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    sponsors = {r["ticker"] for r in rows}
    assets = {r["asset"] for r in rows}
    print(f"{len(rows)} forward catalysts across {len(sponsors)} sponsors "
          f"and {len(assets)} assets\n")

    print("By catalyst source channel:")
    for source, n in Counter(r["source"] for r in rows).most_common():
        print(f"  {source:16} {n}")

    print("\nTop sponsors by near-term catalyst count:")
    for ticker, n in Counter(r["ticker"] for r in rows).most_common(5):
        print(f"  {ticker:6} {n}")

    print("\nThe five nearest-term catalysts:")
    for r in sorted(rows, key=lambda r: r["event_date"])[:5]:
        print(f"  {r['event_date']}  {r['ticker']:6} {r['asset']:20} "
              f"{r['event_type']:8} [{r['confidence']}]")

    print("\nExample — one catalyst with its provenance:")
    r = sorted(rows, key=lambda r: r["event_date"])[0]
    print(f"  {r['asset']} ({r['ticker']}) - {r['event_type']} on {r['event_date']}")
    print(f"    disclosed as : {r['event_window']} (precision: {r['date_precision']})")
    print(f"    source       : {r['source']}")
    print(f"    verify at    : {r['source_url']}")


if __name__ == "__main__":
    main()
