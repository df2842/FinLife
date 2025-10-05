#!/usr/bin/env python3
"""
Sim Topic Counter

Iteratively runs the FinLife simulation several times and counts how many times
AI-generated scenarios (questions) fall into each of the 8 topics:

- Borrowing
- Saving
- Consuming
- Earning
- Go-to info sources
- Investing
- Insuring
- Comprehending risk

Usage examples:
  python sim_topic_counter.py --runs 10                 # Auto-detects mode (server/offline)
  python sim_topic_counter.py --runs 50 --mode server   # Uses running Flask API at http://localhost:5500
  python sim_topic_counter.py --runs 20 --mode offline  # Calls ai_agent directly without server
  python sim_topic_counter.py --base-url http://localhost:5500 --runs 5

Notes:
- Server mode expects the Flask app (python app.py) to be running locally.
- Offline mode simulates ages and generates scenarios via ai_agent. It will fall back to
  built-in scenarios if the AI API is unavailable.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from typing import Dict, List, Any, Optional

import requests

# Attempt to import project modules when running from repo root
try:
    import ai_agent  # type: ignore
except Exception:
    ai_agent = None  # Will only be needed in offline mode


TOPICS = [
    "Borrowing",
    "Saving",
    "Consuming",
    "Earning",
    "Go-to info sources",
    "Investing",
    "Insuring",
    "Comprehending risk",
]

# Keyword heuristics for classifying a scenario into the 8 topics
# The classifier inspects scenario_title, scenario_description, and choice descriptions.
TOPIC_KEYWORDS = {
    "Borrowing": [
        "loan", "borrow", "mortgage", "finance", "apr", "debt", "credit card", "credit line",
    ],
    "Saving": [
        "save", "savings", "emergency fund", "set aside", "rainy day", "high-yield", "deposit $",
    ],
    "Consuming": [
        "buy", "purchase", "spend", "shopping", "vacation", "car", "appliance", "rent", "lease",
    ],
    "Earning": [
        "salary", "income", "job", "wage", "promotion", "offer", "side hustle", "overtime",
    ],
    "Go-to info sources": [
        "research", "compare", "reviews", "advisor", "consult", "learn more", "read", "source",
    ],
    "Investing": [
        "invest", "investment", "stock", "bond", "etf", "ira", "401k", "portfolio", "diversify",
    ],
    "Insuring": [
        "insurance", "insured", "premium", "deductible", "coverage", "policy",
    ],
    "Comprehending risk": [
        "risk", "risky", "volatile", "uncertain", "probability", "tolerance",
    ],
}


def _normalize_text(s: str) -> str:
    return (s or "").lower()


def _event_text(event: Dict[str, Any]) -> str:
    parts: List[str] = []
    parts.append(_normalize_text(event.get("scenario_title", "")))
    parts.append(_normalize_text(event.get("scenario_description", "")))
    for ch in event.get("choices", []) or []:
        parts.append(_normalize_text(ch.get("description", "")))
        fi = ch.get("financial_impact") or {}
        if isinstance(fi, dict):
            # capture both MCQ and job shapes
            for k in ("description", "title"):
                if k in fi:
                    parts.append(_normalize_text(str(fi[k])))
    return "\n".join(p for p in parts if p)


def classify_event(event: Dict[str, Any]) -> List[str]:
    """Return a list of topic labels matched for the given event.

    - Job scenarios (choices with financial_impact.income) are mapped to Earning.
    - MCQ scenarios are classified via keyword heuristics; multiple topics may match.
    - If nothing matches, returns an empty list.
    """
    topics: List[str] = []

    # Detect job scenario by shape (financial_impact has 'income' for job events)
    choices = event.get("choices") or []
    if any(isinstance(c, dict) and isinstance(c.get("financial_impact"), dict) and "income" in c["financial_impact"] for c in choices):
        return ["Earning"]

    text = _event_text(event)

    for topic, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                topics.append(topic)
                break

    # De-duplicate while preserving order
    seen = set()
    uniq = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


class ServerSimulator:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health(self) -> bool:
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=10)
            return r.status_code == 200 or r.status_code == 503  # degraded still okay
        except requests.RequestException:
            return False

    def start_game(self) -> str:
        first = random.choice(["Alex", "Sam", "Taylor", "Jordan", "Riley", "Morgan"]) + str(random.randint(1, 999))
        last = random.choice(["Lee", "Kim", "Patel", "Garcia", "Nguyen", "Brown"]) + str(random.randint(1, 999))
        payload = {"firstName": first, "lastName": last}
        resp = self.session.post(f"{self.base_url}/game/start", json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data["gameId"]

    def advance_year(self, game_id: str) -> Dict[str, Any]:
        resp = self.session.post(f"{self.base_url}/game/advance-year", json={"gameId": game_id}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def run_once(self, max_years: int = 80) -> List[Dict[str, Any]]:
        game_id = self.start_game()
        events: List[Dict[str, Any]] = []
        for _ in range(max_years):
            data = self.advance_year(game_id)
            if data.get("gameOver"):
                break
            # When not gameOver, a scenario should be present under nextEvent
            if "nextEvent" in data and isinstance(data["nextEvent"], dict):
                events.append(data["nextEvent"])  # collect for classification
        return events


class OfflineSimulator:
    START_AGE = 16
    END_AGE = 67

    def __init__(self):
        if ai_agent is None:
            raise RuntimeError("ai_agent module unavailable; run from project root or use server mode.")
        # Baseline state similar to app.py
        self.balance = 50_000
        self.income = 0
        self.job_title = "Unemployed"
        self.loans: List[Dict[str, Any]] = []
        self.life_events: List[str] = []

    @staticmethod
    def _event_type_and_specifier(age: int) -> (str, str):
        event_type = "mcq"
        specifier = "N/A"
        if age == 18:
            specifier = "paying or borrowing for college"
        elif age == 21:
            specifier = "paying or borrowing for a car"
        elif age == 38:
            specifier = "paying or borrowing for a house"
        elif (age <= 30 and age % 2 == 0) or (age > 30 and age % 5 == 0):
            event_type = "job"
        return event_type, specifier

    def _apply_job_choice(self, event: Dict[str, Any]):
        # Simple: accept the best income choice
        best = None
        for ch in event.get("choices", []) or []:
            fi = ch.get("financial_impact") or {}
            if isinstance(fi, dict) and "income" in fi:
                if best is None or fi["income"] > best["financial_impact"]["income"]:
                    best = ch
        if best:
            fi = best["financial_impact"]
            self.income = int(fi.get("income", self.income))
            self.job_title = str(fi.get("title", self.job_title))
            self.life_events.append(f"Became a {self.job_title}")

    def run_once(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        year = 0
        for age in range(self.START_AGE, self.END_AGE):
            year += 1
            event_type, specifier = self._event_type_and_specifier(age)
            sim_date = f"{2024 + year}-01-01"
            try:
                if event_type == "job":
                    # Fix: ai_agent.generate_jo expects (name, age, income, title, life_events)
                    name = f"Player{random.randint(1,999)}"
                    event = ai_agent.generate_jo(name, age, self.income, self.job_title, self.life_events)
                    if isinstance(event, dict):
                        events.append(event)
                        # Optionally apply choice to evolve state
                        self._apply_job_choice(event)
                else:
                    # Fix: ai_agent.generate_mcq expects (name, age, date, balance, income, life_events, specifier)
                    name = f"Player{random.randint(1,999)}"
                    event = ai_agent.generate_mcq(name, age, sim_date, self.balance, self.income, self.life_events, specifier)
                    if isinstance(event, dict):
                        events.append(event)
            except Exception:
                # If AI fails unexpectedly, skip this year
                continue
        return events


def aggregate_counts(all_events: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {t: 0 for t in TOPICS}
    for ev in all_events:
        topics = classify_event(ev)
        for t in topics:
            if t in counts:
                counts[t] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description="Run FinLife simulations and count AI question topics.")
    parser.add_argument("--runs", type=int, default=10, help="Number of simulation runs")
    parser.add_argument("--base-url", type=str, default="http://localhost:5500", help="FinLife server base URL")
    parser.add_argument("--mode", choices=["auto", "server", "offline"], default="auto", help="Run mode")
    args = parser.parse_args()

    all_events: List[Dict[str, Any]] = []

    mode = args.mode
    server = ServerSimulator(args.base_url)

    if mode == "auto":
        mode = "server" if server.health() else "offline"
        print(f"[info] Auto-selected mode: {mode}")

    if mode == "server":
        if not server.health():
            print("[error] Server not reachable at /health. Start the app (python app.py) or use --mode offline.")
            sys.exit(2)
        for i in range(args.runs):
            try:
                events = server.run_once()
                all_events.extend(events)
                print(f"[run {i+1}/{args.runs}] collected {len(events)} events")
                time.sleep(0.2)  # gentle pacing
            except Exception as e:
                print(f"[warn] Run {i+1} failed: {e}")
    else:
        if ai_agent is None:
            print("[error] Offline mode requires running from repo root (ai_agent import failed).")
            sys.exit(3)
        for i in range(args.runs):
            try:
                sim = OfflineSimulator()
                events = sim.run_once()
                all_events.extend(events)
                print(f"[run {i+1}/{args.runs}] collected {len(events)} events (offline)")
            except Exception as e:
                print(f"[warn] Offline run {i+1} failed: {e}")

    counts = aggregate_counts(all_events)

    total_events = len(all_events)
    print("\n=== Topic Counts ===")
    for t in TOPICS:
        print(f"{t}: {counts[t]}")
    print(f"Total events: {total_events}")

    # Also show coverage ratio per topic
    print("\n=== Topic Coverage (percent of events matching topic) ===")
    if total_events == 0:
        print("No events collected.")
    else:
        for t in TOPICS:
            pct = 100.0 * counts[t] / total_events
            print(f"{t}: {pct:.1f}%")


if __name__ == "__main__":
    main()
