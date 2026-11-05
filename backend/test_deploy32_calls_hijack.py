"""Targeted tests for deploy 32 (2026-11-05): Log Call modal id hijack.

Client report: a Lead Owner opening "Log Activity" from the leads list
and saving got "Access denied", while API-level checks (deploy 28)
passed for the owner's own leads. Root cause was in calls.js: a
leftover "static HTML showcase" block attached an extra click handler
to every Log Activity / Call Now button inside .chart-card elements 1s
after page load and called showCallModal(index + 1) — a MOCK lead id.
Attached after leads.js's real handlers, the mock id overwrote
#call-lead-id, so the form posted to another owner's lead (403), or
silently to a wrong claimable lead. Deploy 32 removes the block and
cache-busts calls.js (v6 -> v7) in leads.html.

Run from backend/:
    venv/bin/python test_deploy32_calls_hijack.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

STATIC = os.path.join(os.path.dirname(__file__), 'app', 'static')
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def read(rel):
    with open(os.path.join(STATIC, rel), encoding='utf-8') as f:
        return f.read()


def main():
    calls_js = read('assets/js/calls.js')
    leads_html = read('leads.html')
    leads_js = read('assets/js/leads.js')

    check('showcase mock-id block removed from calls.js',
          'showCallModal(index' not in calls_js and 'Mock ID 1, 2, 3' not in calls_js)
    check('no stray chart-card click attach left in calls.js',
          "querySelectorAll('.chart-card')" not in calls_js)
    check('showCallModal still defined in calls.js',
          'window.showCallModal = function(leadId)' in calls_js)
    check('showCallModal writes the passed id into #call-lead-id',
          "document.getElementById('call-lead-id').value = leadId" in calls_js)
    check('leads.js opens the modal with the real lead.id',
          'showCallModal(lead.id)' in leads_js)
    check('lead cards carry the Log Activity button (hijack target existed)',
          'Log Activity' in leads_js and 'chart-card' in leads_js)
    check('leads.html cache-busts calls.js to v7',
          '/assets/js/calls.js?v=7' in leads_html)

    passed = sum(1 for _, ok in CHECKS if ok)
    print(f"\n{passed}/{len(CHECKS)} checks passed")
    sys.exit(0 if passed == len(CHECKS) else 1)


if __name__ == '__main__':
    main()
