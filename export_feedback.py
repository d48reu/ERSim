#!/usr/bin/env python3
"""
Dump captured alpha feedback as CSV.

Usage:
  python export_feedback.py > feedback.csv
  ERSIM_FEEDBACK_DB=/path/to/feedback.db python export_feedback.py
"""

from api.feedback_store import export_feedback_csv


def main() -> None:
    print(export_feedback_csv(), end="")


if __name__ == "__main__":
    main()
