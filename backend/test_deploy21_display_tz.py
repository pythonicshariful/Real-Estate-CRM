"""Targeted tests for deploy 21 (2026-11-04): pin every remaining
event/timestamp formatter in events.html and lead-details.html to
Asia/Dhaka so displayed times never shift with the viewer's PC timezone.

Background: deploy 20 fixed the SAVE path (create forms send the raw
datetime-local value; the backend interprets naive input as Dhaka wall
time) and the events calendar grid already pins timeZone 'Asia/Dhaka'
(FullCalendar config). But the detail renderings still formatted with
browser-local toLocaleString/toLocaleDateString:
- events.html showEventDetails modal (event start/end)
- lead-details.html lead Events list, history timeline timestamps,
  note dates and coaching session dates.

These are static content checks (the formatting lives in inline page
scripts, so file content is the behaviour under test). leads.js is
checked as a regression guard: its formatters already pin Asia/Dhaka
and must stay that way.

Run: venv/bin/python test_deploy21_display_tz.py  (from backend/)
"""
import os
import re
import sys

STATIC = os.path.join(os.path.dirname(__file__), 'app', 'static')
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def read_static(rel):
    with open(os.path.join(STATIC, rel), encoding='utf-8') as f:
        return f.read()


def locale_calls(html):
    """Every toLocale(String|DateString|TimeString)(...) call text in the file."""
    return re.findall(r'toLocale(?:String|DateString|TimeString)\([^)]*\)', html)


def main():
    # ── events.html: showEventDetails start/end pinned ───────────────
    events_html = read_static('events.html')
    check("events.html details start pinned to Asia/Dhaka",
          "new Date(d.start).toLocaleString([], { dateStyle: 'medium', "
          "timeStyle: 'short', timeZone: 'Asia/Dhaka' })" in events_html)
    check("events.html details end pinned to Asia/Dhaka",
          "new Date(d.end).toLocaleString([], { dateStyle: 'medium', "
          "timeStyle: 'short', timeZone: 'Asia/Dhaka' })" in events_html)
    datestyle_calls = [c for c in locale_calls(events_html) if 'dateStyle' in c]
    check("events.html has exactly the two dateStyle formatters, both pinned",
          len(datestyle_calls) == 2
          and all("timeZone: 'Asia/Dhaka'" in c for c in datestyle_calls),
          f"found {len(datestyle_calls)}: {datestyle_calls}")
    check("events.html keeps the FullCalendar Asia/Dhaka grid pin",
          "timeZone: 'Asia/Dhaka'" in events_html)

    # ── lead-details.html: all four sites pinned ─────────────────────
    details_html = read_static('lead-details.html')
    check("lead-details.html events list dt pinned to Asia/Dhaka",
          "start.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short', "
          "timeZone: 'Asia/Dhaka' })" in details_html)
    check("lead-details.html timeline item.date pinned to Asia/Dhaka",
          "new Date(item.date).toLocaleString([], { timeZone: 'Asia/Dhaka' })"
          in details_html)
    check("lead-details.html note created_at pinned to Asia/Dhaka",
          "new Date(n.created_at).toLocaleDateString([], { timeZone: 'Asia/Dhaka' })"
          in details_html)
    check("lead-details.html session_date pinned to Asia/Dhaka",
          "new Date(c.session_date).toLocaleDateString([], { timeZone: 'Asia/Dhaka' })"
          in details_html)
    check("lead-details.html has no bare (option-less) locale date calls left",
          'toLocaleString()' not in details_html
          and 'toLocaleDateString()' not in details_html)
    ld_calls = locale_calls(details_html)
    check("every locale date call in lead-details.html is Dhaka-pinned",
          len(ld_calls) == 4 and all('Asia/Dhaka' in c for c in ld_calls),
          f"found {len(ld_calls)}: {ld_calls}")

    # ── leads.js regression guard: formatters already pin Dhaka ──────
    leads_js = read_static(os.path.join('assets', 'js', 'leads.js'))
    check("leads.js main formatter still pins Asia/Dhaka",
          re.search(r"toLocaleString\('en-US', \{[^}]*timeZone: 'Asia/Dhaka'",
                    leads_js) is not None)
    tz_pins = leads_js.count("timeZone: 'Asia/Dhaka'")
    check("leads.js Dhaka 'today' helpers still pinned",
          tz_pins >= 3, f"occurrences={tz_pins}")

    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
