"""
Unit tests for the analysis pipeline.

Run with: pytest analysis/tests/ -v
"""
import json
import pytest
from analyze import (
    load_events, clean_events, meta_stats,
    build_sessions, build_journeys, most_common_journeys,
    funnel_analysis, detect_issues, surface_behaviors,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def evt(session_id, user_id, path, css=None, value=None, text=None,
        event_time="2024-01-01 10:00:00"):
    return {
        "uuid":       f"uuid-{session_id}-{path}-{css}",
        "user_id":    user_id,
        "session_id": session_id,
        "path":       path,
        "css":        css,
        "text":       text,
        "value":      value,
        "event_time": event_time,
    }


def all_events(sessions: dict) -> list:
    return [e for evts in sessions.values() for e in evts]


# ── load_events ───────────────────────────────────────────────────────────────

class TestLoadEvents:
    def test_loads_valid_jsonl(self, tmp_path):
        f = tmp_path / "events.json"
        f.write_text('{"a": 1}\n{"b": 2}\n')
        result = load_events(str(f))
        assert len(result) == 2
        assert result[0] == {"a": 1}

    def test_skips_empty_lines(self, tmp_path):
        f = tmp_path / "events.json"
        f.write_text('{"a": 1}\n\n{"b": 2}\n')
        assert len(load_events(str(f))) == 2

    def test_skips_malformed_lines(self, tmp_path):
        f = tmp_path / "events.json"
        f.write_text('{"a": 1}\nnot-json\n{"b": 2}\n')
        result = load_events(str(f))
        assert len(result) == 2

    def test_empty_file(self, tmp_path):
        f = tmp_path / "events.json"
        f.write_text("")
        assert load_events(str(f)) == []


# ── clean_events ──────────────────────────────────────────────────────────────

class TestCleanEvents:
    def test_preserves_all_events(self):
        events = [
            evt("s1", "u1", "/"),
            {**evt("s2", "u2", "/products"), "event_time": None},
        ]
        assert len(clean_events(events)) == 2

    def test_null_timestamp_kept_as_none(self):
        events = [{**evt("s1", "u1", "/"), "event_time": None}]
        result = clean_events(events)
        assert result[0]["event_time"] is None

    def test_missing_event_time_key_flagged(self):
        event = evt("s1", "u1", "/")
        del event["event_time"]
        result = clean_events([event])
        assert result[0].get("event_time") is None


# ── meta_stats ────────────────────────────────────────────────────────────────

class TestMetaStats:
    def test_counts_events_users_sessions(self):
        events = [
            evt("s1", "u1", "/"),
            evt("s1", "u1", "/products"),
            evt("s2", "u2", "/"),
        ]
        meta = meta_stats(events)
        assert meta["total_events"]   == 3
        assert meta["total_users"]    == 2
        assert meta["total_sessions"] == 2

    def test_time_range(self):
        events = [
            evt("s1", "u1", "/", event_time="2024-01-01 09:00:00"),
            evt("s1", "u1", "/", event_time="2024-01-01 11:00:00"),
        ]
        meta = meta_stats(events)
        assert meta["time_range"]["start"] == "2024-01-01 09:00:00"
        assert meta["time_range"]["end"]   == "2024-01-01 11:00:00"

    def test_missing_timestamps_counted(self):
        events = [
            evt("s1", "u1", "/"),
            {**evt("s2", "u2", "/"), "event_time": None},
        ]
        meta = meta_stats(events)
        assert meta["missing_timestamps"] == 1


# ── build_sessions ────────────────────────────────────────────────────────────

class TestBuildSessions:
    def test_groups_by_session_id(self):
        events = [evt("s1", "u1", "/"), evt("s2", "u2", "/"), evt("s1", "u1", "/products")]
        sessions = build_sessions(events)
        assert set(sessions.keys()) == {"s1", "s2"}
        assert len(sessions["s1"]) == 2

    def test_sorts_by_event_time(self):
        events = [
            evt("s1", "u1", "/products", event_time="2024-01-01 10:05:00"),
            evt("s1", "u1", "/",         event_time="2024-01-01 10:00:00"),
        ]
        sessions = build_sessions(events)
        assert sessions["s1"][0]["path"] == "/"
        assert sessions["s1"][1]["path"] == "/products"

    def test_null_timestamps_sorted_last(self):
        events = [
            {**evt("s1", "u1", "/late"), "event_time": None},
            evt("s1", "u1", "/",         event_time="2024-01-01 10:00:00"),
        ]
        sessions = build_sessions(events)
        assert sessions["s1"][0]["path"] == "/"
        assert sessions["s1"][1]["path"] == "/late"


# ── build_journeys ────────────────────────────────────────────────────────────

class TestBuildJourneys:
    def test_deduplicates_consecutive_pages(self):
        sessions = {"s1": [
            evt("s1", "u1", "/"),
            evt("s1", "u1", "/"),
            evt("s1", "u1", "/products"),
        ]}
        journeys = build_journeys(sessions)
        assert journeys[0]["pages"] == ["/", "/products"]

    def test_non_consecutive_revisit_kept(self):
        sessions = {"s1": [
            evt("s1", "u1", "/"),
            evt("s1", "u1", "/products"),
            evt("s1", "u1", "/"),
        ]}
        journeys = build_journeys(sessions)
        assert journeys[0]["pages"] == ["/", "/products", "/"]

    def test_flags_error_on_checkout(self):
        sessions = {"s1": [evt("s1", "u1", "/checkout", css="div.error-message")]}
        journeys = build_journeys(sessions)
        assert journeys[0]["has_error"] is True

    def test_flags_completed_order(self):
        sessions = {"s1": [evt("s1", "u1", "/checkout", css="button.place-order")]}
        journeys = build_journeys(sessions)
        assert journeys[0]["completed_order"] is True

    def test_no_flags_on_clean_session(self):
        sessions = {"s1": [evt("s1", "u1", "/")]}
        journeys = build_journeys(sessions)
        assert journeys[0]["has_error"]       is False
        assert journeys[0]["completed_order"] is False

    def test_event_count(self):
        sessions = {"s1": [evt("s1", "u1", "/"), evt("s1", "u1", "/products")]}
        journeys = build_journeys(sessions)
        assert journeys[0]["event_count"] == 2


# ── most_common_journeys ──────────────────────────────────────────────────────

class TestMostCommonJourneys:
    def test_top_n_respected(self):
        journeys = [{"pages": ["/", "/products/x"]}] * 3 + [{"pages": ["/"]}] * 2
        assert len(most_common_journeys(journeys, top_n=1)) == 1

    def test_ordering_by_count(self):
        journeys = [{"pages": ["/a"]}] + [{"pages": ["/b"]}, {"pages": ["/b"]}]
        result = most_common_journeys(journeys, top_n=2)
        assert result[0]["path"]  == ["/b"]
        assert result[0]["count"] == 2
        assert result[1]["path"]  == ["/a"]

    def test_product_pages_normalized(self):
        journeys = [
            {"pages": ["/", "/products/phone", "/cart"]},
            {"pages": ["/", "/products/laptop", "/cart"]},
        ]
        result = most_common_journeys(journeys, top_n=5)
        assert len(result) == 1
        assert result[0]["path"]  == ["/", "/products/*", "/cart"]
        assert result[0]["count"] == 2

    def test_pct_included(self):
        journeys = [{"pages": ["/", "/products/x"]}] * 2 + [{"pages": ["/"]}] * 2
        result = most_common_journeys(journeys, top_n=5)
        assert all("pct" in r for r in result)

    def test_empty_journeys(self):
        assert most_common_journeys([]) == []


# ── funnel_analysis ───────────────────────────────────────────────────────────

class TestFunnelAnalysis:
    def _sessions(self, paths_by_id):
        return {
            sid: [evt(sid, "u1", p) for p in paths]
            for sid, paths in paths_by_id.items()
        }

    def test_full_journey_counted_at_every_step(self):
        sessions = self._sessions({"s1": ["/", "/products/x", "/cart", "/checkout"]})
        counts = {s["step"]: s["sessions"] for s in funnel_analysis(sessions)["steps"]}
        assert counts["homepage"] == 1
        assert counts["products"] == 1
        assert counts["cart"]     == 1
        assert counts["checkout"] == 1

    def test_sequential_drop_at_first_missing_step(self):
        sessions = self._sessions({
            "s1": ["/", "/products/x", "/cart", "/checkout"],
            "s2": ["/", "/products/x"],
        })
        counts = {s["step"]: s["sessions"] for s in funnel_analysis(sessions)["steps"]}
        assert counts["homepage"] == 2
        assert counts["products"] == 2
        assert counts["cart"]     == 1
        assert counts["checkout"] == 1

    def test_direct_checkout_entry_not_counted(self):
        # Sequential funnel: session starting at /checkout has no homepage → drops at step 0
        sessions = {"s1": [evt("s1", "u1", "/checkout")]}
        counts = {s["step"]: s["sessions"] for s in funnel_analysis(sessions)["steps"]}
        assert counts["homepage"] == 0
        assert counts["checkout"] == 0

    def test_dropoff_is_non_negative(self):
        sessions = self._sessions({
            "s1": ["/", "/products/x", "/cart", "/checkout"],
            "s2": ["/"],
        })
        for step in funnel_analysis(sessions)["steps"]:
            assert step["dropoff_from_prev"] >= 0

    def test_checkout_conversion_rate(self):
        sessions = {
            "s1": [
                evt("s1", "u1", "/"),
                evt("s1", "u1", "/products/x"),
                evt("s1", "u1", "/cart"),
                evt("s1", "u1", "/checkout"),
                evt("s1", "u1", "/checkout", css="button.place-order"),
            ],
            "s2": [
                evt("s2", "u2", "/"),
                evt("s2", "u2", "/products/x"),
                evt("s2", "u2", "/cart"),
                evt("s2", "u2", "/checkout"),
            ],
        }
        assert funnel_analysis(sessions)["checkout_conversion_rate"] == 50.0

    def test_checkout_outcomes_completed(self):
        sessions = {"s1": [evt("s1", "u1", "/checkout", css="button.place-order")]}
        outcomes = funnel_analysis(sessions)["checkout_outcomes"]
        assert outcomes.get("completed") == 1

    def test_checkout_outcomes_cancelled(self):
        sessions = {"s1": [evt("s1", "u1", "/checkout", css="button.cancel-order")]}
        outcomes = funnel_analysis(sessions)["checkout_outcomes"]
        assert outcomes.get("cancelled") == 1

    def test_checkout_outcomes_silent_drop(self):
        sessions = {"s1": [evt("s1", "u1", "/checkout")]}
        outcomes = funnel_analysis(sessions)["checkout_outcomes"]
        assert outcomes.get("dropped_silently") == 1

    def test_empty_sessions(self):
        funnel = funnel_analysis({})
        assert funnel["checkout_conversion_rate"] == 0
        for step in funnel["steps"]:
            assert step["sessions"] == 0


# ── detect_issues ─────────────────────────────────────────────────────────────

class TestDetectIssues:
    def _ids(self, sessions):
        return [i["id"] for i in detect_issues(sessions)]

    def test_checkout_error_abandonment_detected(self):
        sessions = {"s1": [
            evt("s1", "u1", "/checkout", css="div.error-message"),
            evt("s1", "u1", "/checkout"),
        ]}
        assert "checkout_error_abandonment" in self._ids(sessions)

    def test_no_abandonment_when_order_placed(self):
        sessions = {"s1": [
            evt("s1", "u1", "/checkout", css="div.error-message"),
            evt("s1", "u1", "/checkout", css="button.place-order"),
        ]}
        assert "checkout_error_abandonment" not in self._ids(sessions)

    def test_direct_checkout_entry_detected(self):
        sessions = {"s1": [evt("s1", "u1", "/checkout")]}
        assert "direct_checkout_entry" in self._ids(sessions)

    def test_no_direct_checkout_when_preceded_by_browse(self):
        sessions = {"s1": [
            evt("s1", "u1", "/", event_time="10:00"),
            evt("s1", "u1", "/checkout", event_time="10:05"),
        ]}
        assert "direct_checkout_entry" not in self._ids(sessions)

    def test_faq_broken_detected(self):
        sessions = {"s1": [
            evt("s1", "u1", "/faq", css="a.question"),
            evt("s1", "u1", "/faq", css="div.error-message"),
        ]}
        assert "faq_broken" in self._ids(sessions)

    def test_faq_ok_when_answer_loads(self):
        sessions = {"s1": [
            evt("s1", "u1", "/faq", css="a.question"),
            evt("s1", "u1", "/faq", css="div.answer"),
        ]}
        assert "faq_broken" not in self._ids(sessions)

    def test_language_switch_error_detected(self):
        sessions = {"s1": [
            evt("s1", "u1", "/settings", css="select.language", value="ru"),
            evt("s1", "u1", "/settings", css="div.error-message"),
        ]}
        assert "language_switch_error" in self._ids(sessions)

    def test_random_page_confusion_detected_for_question_marks(self):
        sessions = {"s1": [evt("s1", "u1", "/random", value="???")]}
        assert "random_page_confusion" in self._ids(sessions)

    def test_random_page_confusion_detected_for_error(self):
        sessions = {"s1": [evt("s1", "u1", "/random", css="div.error-message")]}
        assert "random_page_confusion" in self._ids(sessions)

    def test_no_false_positives_on_clean_session(self):
        sessions = {"s1": [
            evt("s1", "u1", "/"),
            evt("s1", "u1", "/products/phone"),
            evt("s1", "u1", "/cart",     css="button.add-to-cart"),
            evt("s1", "u1", "/checkout", css="button.place-order"),
        ]}
        assert detect_issues(sessions) == []

    def test_issue_has_required_fields(self):
        sessions = {"s1": [
            evt("s1", "u1", "/checkout", css="div.error-message"),
        ]}
        for issue in detect_issues(sessions):
            assert "id"                in issue
            assert "severity"          in issue
            assert "title"             in issue
            assert "description"       in issue
            assert "recommendation"    in issue
            assert "affected_sessions" in issue


# ── surface_behaviors ─────────────────────────────────────────────────────────

class TestSurfaceBehaviors:
    def _ids(self, sessions):
        return [b["id"] for b in surface_behaviors(sessions, all_events(sessions))]

    def test_negative_comment_then_purchase(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="textarea.comment", value="This is mediocre"),
            evt("s1", "u1", "/checkout",       css="button.place-order"),
        ]}
        assert "negative_comment_then_purchase" in self._ids(sessions)

    def test_positive_comment_not_flagged(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="textarea.comment", value="Great product!"),
            evt("s1", "u1", "/checkout",       css="button.place-order"),
        ]}
        assert "negative_comment_then_purchase" not in self._ids(sessions)

    def test_negative_comment_without_purchase_not_flagged(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="textarea.comment", value="mediocre quality"),
        ]}
        assert "negative_comment_then_purchase" not in self._ids(sessions)

    def test_cart_then_logout(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="button.add-to-cart"),
            evt("s1", "u1", "/",               css="button.logout"),
        ]}
        assert "cart_then_logout" in self._ids(sessions)

    def test_cart_then_checkout_not_flagged(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="button.add-to-cart"),
            evt("s1", "u1", "/checkout",       css="button.place-order"),
        ]}
        assert "cart_then_logout" not in self._ids(sessions)

    def test_random_as_search_entry(self):
        sessions = {"s1": [evt("s1", "u1", "/random", value="wireless headphones")]}
        assert "random_as_search_entry" in self._ids(sessions)

    def test_confusion_value_not_counted_as_search(self):
        sessions = {"s1": [evt("s1", "u1", "/random", value="???")]}
        assert "random_as_search_entry" not in self._ids(sessions)

    def test_comment_without_purchase_detected(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="textarea.comment", value="Great design"),
        ]}
        assert "comment_without_purchase" in self._ids(sessions)

    def test_comment_with_purchase_not_flagged(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="textarea.comment", value="Great design"),
            evt("s1", "u1", "/checkout",       css="button.place-order"),
        ]}
        assert "comment_without_purchase" not in self._ids(sessions)

    def test_behavior_has_required_fields(self):
        sessions = {"s1": [
            evt("s1", "u1", "/products/phone", css="button.add-to-cart"),
            evt("s1", "u1", "/",               css="button.logout"),
        ]}
        for b in surface_behaviors(sessions, all_events(sessions)):
            assert "id"          in b
            assert "title"       in b
            assert "description" in b
            assert "insight"     in b


# ── Integration ───────────────────────────────────────────────────────────────

class TestPipelineIntegration:
    def test_main_produces_valid_insights_json(self, tmp_path, monkeypatch, capsys):
        events = [
            evt("s1", "u1", "/"),
            evt("s1", "u1", "/products/phone"),
            evt("s1", "u1", "/cart",     css="button.add-to-cart"),
            evt("s1", "u1", "/checkout"),
            evt("s1", "u1", "/checkout", css="button.place-order"),
            evt("s2", "u2", "/checkout", css="div.error-message"),
            evt("s2", "u2", "/faq",      css="a.question"),
            evt("s2", "u2", "/faq",      css="div.error-message"),
        ]
        input_file  = tmp_path / "sessions.json"
        output_file = tmp_path / "insights.json"
        input_file.write_text("\n".join(json.dumps(e) for e in events))

        import analyze
        monkeypatch.setattr(analyze, "INPUT_PATH",  str(input_file))
        monkeypatch.setattr(analyze, "OUTPUT_PATH", str(output_file))
        analyze.main()

        assert output_file.exists()
        with output_file.open() as f:
            insights = json.load(f)

        assert "generated_at" in insights
        for key in ("meta", "funnel", "journeys", "issues", "behaviors"):
            assert key in insights, f"missing key: {key}"

        assert insights["meta"]["total_events"]   == 8
        assert insights["meta"]["total_sessions"] == 2

        issue_ids = [i["id"] for i in insights["issues"]]
        assert "faq_broken"                 in issue_ids
        assert "checkout_error_abandonment" in issue_ids

    def test_main_handles_empty_input(self, tmp_path, monkeypatch, capsys):
        input_file  = tmp_path / "sessions.json"
        output_file = tmp_path / "insights.json"
        input_file.write_text("")

        import analyze
        monkeypatch.setattr(analyze, "INPUT_PATH",  str(input_file))
        monkeypatch.setattr(analyze, "OUTPUT_PATH", str(output_file))
        analyze.main()

        with output_file.open() as f:
            insights = json.load(f)
        assert insights["meta"]["total_events"] == 0
        assert insights["issues"]               == []
        assert insights["behaviors"]            == []
