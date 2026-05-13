"""
Tandem Explorer - Data Analysis Pipeline
=================================================
Parses session interaction data from a JSONL file and produces a structured
insights.json consumed by the Next.js dashboard.

Pipeline:
  1. Load & clean        — parse JSONL, handle malformed lines, flag null timestamps
  2. Session reconstruction — group by session_id, sort by time, build journey objects
                             and compute most_common_journeys (product paths normalized to /products/*)
  3. Funnel analysis     — sequential conversion funnel + checkout outcome breakdown
  4. Issue detection     — rule-based detection of bugs and friction patterns with severity + recommendations
  5. Behavior surfacing  — cross-session behavioral patterns with product insights

Output: insights.json with keys: meta, funnel, journeys, issues, behaviors
"""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime

# CSS selectors — single source of truth
CSS_ERROR    = "div.error-message"
CSS_ORDER    = "button.place-order"
CSS_CANCEL   = "button.cancel-order"
CSS_RETRY    = "button.retry"
CSS_CART     = "button.add-to-cart"
CSS_LOGOUT   = "button.logout"
CSS_COMMENT  = "textarea.comment"
CSS_LANGUAGE = "select.language"
CSS_FAQ_Q    = "a.question"
CSS_SHIPPING = "#shipping-address"

NEGATIVE_WORDS = ["mediocre", "confusing", "sticky", "blurry", "not impressed"]

# Config

INPUT_PATH  = os.path.join(os.path.dirname(__file__), "../data/sessions.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output/insights.json")

# 1. Load & Clean

def load_events(path: str) -> list[dict]:
    events = []
    skipped = 0
    with open(path) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                events.append(e)
            except json.JSONDecodeError:
                skipped += 1
                print(f"  [warn] skipped malformed line {i+1}")
    print(f"  Loaded {len(events)} events ({skipped} skipped)")
    return events


def clean_events(events: list[dict]) -> list[dict]:
    cleaned = []
    null_timestamps = 0
    for e in events:
        if not e.get("event_time"):
            null_timestamps += 1
            e["event_time"] = None  # keep but flag
        cleaned.append(e)
    print(f"  {null_timestamps} event(s) with missing timestamp")
    return cleaned


def meta_stats(events: list[dict]) -> dict:
    times = [e["event_time"] for e in events if e.get("event_time")]
    return {
        "total_events":   len(events),
        "total_users":    len(set(e["user_id"]   for e in events)),
        "total_sessions": len(set(e["session_id"] for e in events)),
        "time_range": {
            "start": min(times) if times else None,
            "end":   max(times) if times else None,
        },
        "missing_timestamps": sum(1 for e in events if not e.get("event_time")),
    }

# 2. Session Reconstruction

def build_sessions(events: list[dict]) -> dict[str, list[dict]]:
    sessions = defaultdict(list)
    for e in events:
        sessions[e["session_id"]].append(e)
    # Sort by event_time; put None timestamps last
    for sid in sessions:
        sessions[sid].sort(key=lambda x: x["event_time"] or "9999")
    return sessions


def build_journeys(sessions: dict[str, list[dict]]) -> list[dict]:
    journeys = []
    for sid, evts in sessions.items():
        pages = []
        for e in evts:
            if not pages or pages[-1] != e["path"]:
                pages.append(e["path"])
        journeys.append({
            "session_id": sid,
            "user_id":    evts[0]["user_id"],
            "start_time": evts[0]["event_time"],
            "end_time":   evts[-1]["event_time"],
            "event_count": len(evts),
            "pages":      pages,
            "has_error":  any(e.get("css") == CSS_ERROR for e in evts),
            "completed_order": any(e.get("css") == CSS_ORDER for e in evts),
            "events": [
                {
                    "time":  e.get("event_time"),
                    "path":  e.get("path"),
                    "css":   e.get("css"),
                    "text":  e.get("text"),
                    "value": e.get("value"),
                }
                for e in evts
            ],
        })
    return journeys


def _normalize_page(path: str) -> str:
    return "/products/*" if path.startswith("/products/") else path


def most_common_journeys(journeys: list[dict], top_n: int = 5) -> list[dict]:
    # Normalize product detail pages to /products/* so that sessions going through
    # different products are grouped as the same journey pattern.
    def normalize(pages: list[str]) -> tuple[str, ...]:
        result: list[str] = []
        for p in pages:
            norm = _normalize_page(p)
            if not result or result[-1] != norm:
                result.append(norm)
        return tuple(result)

    path_sequences = Counter(normalize(j["pages"]) for j in journeys)
    total = len(journeys)
    return [
        {"path": list(seq), "count": count, "pct": round(count / total * 100, 1) if total else 0}
        for seq, count in path_sequences.most_common(top_n)
        if seq
    ]

# 3. Funnel Analysis

FUNNEL_STEPS = [
    ("homepage",     lambda evts: any(e["path"] == "/"           for e in evts)),
    ("products",     lambda evts: any(e["path"].startswith("/products") for e in evts)),
    ("cart",         lambda evts: any(e["path"] == "/cart"        for e in evts)),
    ("checkout",     lambda evts: any(e["path"] == "/checkout"    for e in evts)),
    ("order_placed", lambda evts: any(e.get("css") == CSS_ORDER for e in evts)),
]

def funnel_analysis(sessions: dict) -> dict:
    step_counts = {step: 0 for step, _ in FUNNEL_STEPS}
    for evts in sessions.values():
        # Sequential funnel: a session is counted at step N only if it reached 1..N-1.
        # This differs from "any-order" funnels (e.g. Mixpanel default) where each step
        # is counted independently. Sequential is the right choice here because a drop-off
        # rate "X% left between A and B" is only meaningful if those sessions actually
        # reached A. Any-order would let a direct-to-checkout session inflate the
        # checkout count without ever passing through products or cart.
        for step, predicate in FUNNEL_STEPS:
            if predicate(evts):
                step_counts[step] += 1
            else:
                break

    total = len(sessions)
    steps = []
    prev = total
    for step, count in step_counts.items():
        steps.append({
            "step":             step,
            "sessions":         count,
            "pct_of_total":     round(count / total * 100, 1) if total else 0,
            "dropoff_from_prev": round((prev - count) / prev * 100, 1) if prev else 0,
        })
        prev = count

    # Checkout outcomes
    checkout_outcomes = Counter()
    for evts in sessions.values():
        paths = [e["path"] for e in evts]
        css   = [e.get("css") for e in evts]
        if "/checkout" not in paths:
            continue
        if CSS_ORDER in css:
            checkout_outcomes["completed"] += 1
        elif CSS_CANCEL in css:
            checkout_outcomes["cancelled"] += 1
        elif CSS_RETRY in css:
            checkout_outcomes["retried_then_dropped"] += 1
        else:
            checkout_outcomes["dropped_silently"] += 1

    return {
        "steps": steps,
        "checkout_outcomes": dict(checkout_outcomes),
        "checkout_conversion_rate": round(
            step_counts["order_placed"] / step_counts["checkout"] * 100, 1
        ) if step_counts["checkout"] else 0,
    }

# 4. Problematic Patterns

def detect_issues(sessions: dict) -> list[dict]:
    issues = []

    # 4a. Checkout errors leading to abandonment
    checkout_error_abandonments = []
    for sid, evts in sessions.items():
        paths = [e["path"] for e in evts]
        css   = [e.get("css") for e in evts]
        if "/checkout" not in paths:
            continue
        has_error  = any(e.get("css") == CSS_ERROR and e["path"] == "/checkout" for e in evts)
        abandoned  = CSS_ORDER not in css
        if has_error and abandoned:
            checkout_error_abandonments.append(sid)

    if checkout_error_abandonments:
        issues.append({
            "id":       "checkout_error_abandonment",
            "severity": "critical",
            "title":    "Checkout errors causing order abandonment",
            "description": (
                f"{len(checkout_error_abandonments)} session(s) hit an error on /checkout "
                "and never completed their order. Users either cancelled or dropped silently."
            ),
            "affected_sessions": checkout_error_abandonments,
            "recommendation": "Investigate what triggers div.error-message at checkout. "
                              "likely a payment validation or address validation failure. "
                              "Add clearer error messages and inline field validation.",
        })

    # 4b. Sessions starting directly at /checkout
    direct_checkout = []
    for sid, evts in sessions.items():
        if evts[0]["path"] == "/checkout":
            addr = next((e.get("value") for e in evts if e.get("css") == CSS_SHIPPING), None)
            direct_checkout.append({
                "session": sid,
                "first_css": evts[0].get("css"),
                "address_attempted": addr,
            })

    if direct_checkout:
        issues.append({
            "id":       "direct_checkout_entry",
            "severity": "medium",
            "title":    "Sessions landing directly on /checkout without browsing",
            "description": (
                f"{len(direct_checkout)} session(s) started at /checkout - "
                "likely broken bookmarks, email links, or redirects. "
                "Both hit an error immediately."
            ),
            "affected_sessions": [s["session"] for s in direct_checkout],
            "evidence": direct_checkout,
            "recommendation": "Guard /checkout entry: if cart is empty, redirect to / with a "
                              "friendly message. Audit any external links pointing to /checkout.",
        })

    # 4c. FAQ broken
    faq_errors = []
    for sid, evts in sessions.items():
        for i, e in enumerate(evts):
            if (e["path"] == "/faq"
                    and e.get("css") == CSS_FAQ_Q
                    and i + 1 < len(evts)
                    and evts[i+1].get("css") == CSS_ERROR):
                faq_errors.append(sid)

    if faq_errors:
        issues.append({
            "id":       "faq_broken",
            "severity": "high",
            "title":    "FAQ answers fail to load",
            "description": (
                f"{len(faq_errors)} session(s) clicked a FAQ question and immediately got "
                "an error message. The FAQ content is not rendering."
            ),
            "affected_sessions": faq_errors,
            "recommendation": "Check the FAQ answer fetch - likely a broken API call or "
                              "missing content in the CMS.",
        })

    # 4d. Language switcher error
    lang_errors = []
    for sid, evts in sessions.items():
        for i, e in enumerate(evts):
            if (e.get("css") == CSS_LANGUAGE
                    and any(ev.get("css") == CSS_ERROR and ev["path"] == "/settings"
                            for ev in evts[i:])):
                lang_errors.append({
                    "session": sid,
                    "language": e.get("value"),
                })

    if lang_errors:
        issues.append({
            "id":       "language_switch_error",
            "severity": "medium",
            "title":    "Language switching triggers errors on /settings",
            "description": (
                f"{len(lang_errors)} session(s) changed language and encountered an error. "
                f"Languages affected: {list(set(l['language'] for l in lang_errors))}."
            ),
            "affected_sessions": [l["session"] for l in lang_errors],
            "evidence": lang_errors,
            "recommendation": "The language preference save is failing - check the settings "
                              "PUT endpoint and whether all locale codes are supported.",
        })

    # 4e. /random page - user confusion
    random_confused = []
    for sid, evts in sessions.items():
        random_evts = [e for e in evts if e["path"] == "/random"]
        if not random_evts:
            continue
        confusion_signals = [
            e for e in random_evts
            if e.get("value") in ["???", "confused"]
            or e.get("css") == CSS_ERROR
        ]
        if confusion_signals:
            random_confused.append({
                "session": sid,
                "signals": [{"css": e.get("css"), "value": e.get("value")} for e in confusion_signals],
            })

    if random_confused:
        issues.append({
            "id":       "random_page_confusion",
            "severity": "medium",
            "title":    "/random page causing user confusion",
            "description": (
                f"{len(random_confused)} session(s) on /random showed clear confusion signals "
                "(searches for '???' and 'confused', error messages). "
                "The page purpose is unclear or broken."
            ),
            "affected_sessions": [s["session"] for s in random_confused],
            "evidence": random_confused,
            "recommendation": "Either clarify the purpose of /random with better UX copy, "
                              "or redirect it to a valid page if it's a dead route.",
        })

    return issues

# 5. Interesting Behaviors

def conversion_rate(session_list: list) -> float:
    if not session_list:
        return 0
    converted = sum(1 for evts in session_list if any(e.get("css") == CSS_ORDER for e in evts))
    return round(converted / len(session_list) * 100, 1)


def surface_behaviors(sessions: dict, events: list[dict]) -> list[dict]:
    behaviors = []

    # 5a. Negative review → still purchased
    neg_then_buy = []
    for sid, evts in sessions.items():
        comments = [e for e in evts if e.get("css") == CSS_COMMENT and e.get("value")]
        placed   = any(e.get("css") == CSS_ORDER for e in evts)
        for c in comments:
            val = c["value"].lower()
            if any(w in val for w in NEGATIVE_WORDS) and placed:
                neg_then_buy.append({
                    "session": sid,
                    "product": c["path"].replace("/products/", ""),
                    "comment": c["value"],
                })
    if neg_then_buy:
        behaviors.append({
            "id":          "negative_comment_then_purchase",
            "title":       "Users buying despite leaving negative product feedback",
            "description": (
                f"{len(neg_then_buy)} session(s) left a negative comment on a product page "
                "yet completed their purchase. These comments are live friction signals."
            ),
            "evidence": neg_then_buy,
            "insight": "The textarea.comment on product pages is capturing real-time sentiment. "
                       "Consider surfacing these as a CS alert or feeding them into product reviews.",
        })

    # 5b. Add to cart → logout without checkout
    cart_then_logout = []
    for sid, evts in sessions.items():
        css = [e.get("css") for e in evts]
        if CSS_CART in css and CSS_LOGOUT in css and CSS_ORDER not in css:
            cart_then_logout.append(sid)
    if cart_then_logout:
        behaviors.append({
            "id":          "cart_then_logout",
            "title":       "Items added to cart but session ends with logout",
            "description": (
                f"{len(cart_then_logout)} session(s) added items to cart but logged out "
                "without purchasing. Potential cart abandonment worth following up via email."
            ),
            "affected_sessions": cart_then_logout,
            "insight": "If cart state persists after logout, a cart recovery email flow "
                       "could convert these sessions.",
        })

    # 5c. Multi-language users and their conversion
    lang_users = set(
        e["user_id"] for e in events
        if e.get("css") == CSS_LANGUAGE
    )
    lang_sessions    = [evts for evts in sessions.values() if evts[0]["user_id"] in lang_users]
    nonlang_sessions = [evts for evts in sessions.values() if evts[0]["user_id"] not in lang_users]

    if lang_users:
        behaviors.append({
            "id":    "multilingual_user_conversion",
            "title": "International users: higher engagement but language friction",
            "description": (
                f"{len(lang_users)} user(s) changed their language during the session. "
                f"Their checkout conversion rate: {conversion_rate(lang_sessions)}% "
                f"vs {conversion_rate(nonlang_sessions)}% for non-switchers."
            ),
            "insight": "Language-switching users are highly engaged (they invest time in setup) "
                       "but face technical friction on /settings. Fixing the language save bug "
                       "could directly improve international conversion.",
        })

    # 5d. /random used as search entry point
    random_as_search = []
    for sid, evts in sessions.items():
        random_evts = [e for e in evts if e["path"] == "/random" and e.get("value")]
        if random_evts:
            for e in random_evts:
                if e.get("value") not in ["???", "confused"]:
                    random_as_search.append({
                        "session": sid,
                        "search_term": e.get("value"),
                    })
    if random_as_search:
        behaviors.append({
            "id":    "random_as_search_entry",
            "title": "/random page used as an alternative search entry point",
            "description": (
                f"{len(random_as_search)} session(s) used the search bar on /random "
                f"to find products: {[s['search_term'] for s in random_as_search]}."
            ),
            "evidence": random_as_search,
            "insight": "Some users discover /random and use it to navigate. "
                       "If it has a functional search bar, consider making it a proper "
                       "discovery/exploration page rather than leaving it undefined.",
        })

    # 5e. Comments from non-buyers - weakens social proof
    comment_no_buy = []
    for sid, evts in sessions.items():
        comments = [e for e in evts if e.get("css") == CSS_COMMENT and e.get("value")]
        placed   = any(e.get("css") == CSS_ORDER for e in evts)
        if comments and not placed:
            for c in comments:
                comment_no_buy.append({
                    "session": sid,
                    "product": c["path"].replace("/products/", ""),
                    "comment": c["value"],
                })

    if comment_no_buy:
        behaviors.append({
            "id":    "comment_without_purchase",
            "title": "Product comments left by non-buyers",
            "description": (
                f"{len(comment_no_buy)} comment(s) left on product pages by users "
                "who never completed a purchase. These reviews mix with buyer feedback."
            ),
            "evidence": comment_no_buy,
            "insight": "Non-buyer comments are displayed alongside verified purchase reviews, "
                       "weakening social proof. Consider restricting textarea.comment to "
                       "verified buyers, or adding a 'verified purchase' badge to differentiate.",
        })

    return behaviors

# Main

def main():
    print("\n Tandem Explorer Pipeline\n")

    print("[1/5] Loading and cleaning data...")
    events  = load_events(INPUT_PATH)
    events  = clean_events(events)
    meta    = meta_stats(events)
    print(f"      {meta['total_events']} events | {meta['total_users']} users | {meta['total_sessions']} sessions")

    print("[2/5] Reconstructing sessions...")
    sessions = build_sessions(events)
    journeys = build_journeys(sessions)
    top_journeys = most_common_journeys(journeys)

    print("[3/5] Running funnel analysis...")
    funnel = funnel_analysis(sessions)
    print(f"      Checkout conversion rate: {funnel['checkout_conversion_rate']}%")

    print("[4/5] Detecting problematic patterns...")
    issues = detect_issues(sessions)
    print(f"      {len(issues)} issue(s) detected")

    print("[5/5] Surfacing interesting behaviors...")
    behaviors = surface_behaviors(sessions, events)
    print(f"      {len(behaviors)} behavior(s) surfaced")

    insights = {
        "generated_at": datetime.now().isoformat(),
        "meta":         meta,
        "funnel":       funnel,
        "journeys": {
            "most_common": top_journeys,
            "all":         journeys,
        },
        "issues":     issues,
        "behaviors":  behaviors,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    print(f"\n✅ insights.json written to {OUTPUT_PATH}\n")

if __name__ == "__main__":
    main()
