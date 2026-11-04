"""Deploy 22 regression checks — event details modal timezone handling.

Bug: on the Events page, clicking a calendar event opened the details
modal with the time shifted by +6h (e.g. a 3:45 PM event showed 9:45 PM).
Root cause: the FullCalendar eventClick handler passed ev.start/ev.end —
FullCalendar "marker" Date objects whose UTC wall time equals the zoned
(Asia/Dhaka) wall time — into showEventDetails, which then formatted that
instant in Asia/Dhaka, shifting it by the zone offset. The fix passes
ev.startStr/ev.endStr (ISO strings in the calendar's timezone, with the
correct offset) instead.

These are static checks on the served files (the defect is in how the
page's JS moves data between FullCalendar and the modal).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS_HTML = os.path.join(HERE, 'app', 'static', 'events.html')

passed = 0
failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f'  PASS {name}')
    else:
        failed += 1
        print(f'  FAIL {name}')


def main():
    with open(EVENTS_HTML, encoding='utf-8') as f:
        html = f.read()

    # Locate the eventClick handler block.
    m = re.search(r'eventClick:\s*function\s*\(info\)\s*\{(.*?)\n        \}\n', html, re.S)
    check('eventClick handler found', m is not None)
    block = m.group(1) if m else ''

    check('eventClick passes ev.startStr', 'start: ev.startStr' in block)
    check('eventClick passes ev.endStr', 'end: ev.endStr' in block)
    check('eventClick does NOT pass marker Date ev.start',
          'start: ev.start,' not in block and 'start: ev.start\n' not in block)
    check('eventClick does NOT pass marker Date ev.end',
          'end: ev.end,' not in block and 'end: ev.end\n' not in block)

    # The modal formatter itself stays pinned to Asia/Dhaka (deploy 21).
    check('modal start formatter pinned to Asia/Dhaka',
          "new Date(d.start).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Dhaka' })" in html)
    check('modal end formatter pinned to Asia/Dhaka',
          "new Date(d.end).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Dhaka' })" in html)

    # The reminder -> linked-event caller uses API strings (with offsets);
    # it must keep passing ev.start/ev.end from the fetch (not startStr,
    # which does not exist on plain JSON).
    check('reminder linked-event caller still uses API ev.start',
          'title: ev.title, start: ev.start, end: ev.end,' in html)

    # Calendar itself still pinned to Asia/Dhaka.
    check("FullCalendar timeZone is Asia/Dhaka", "timeZone: 'Asia/Dhaka'" in html)

    print(f'\n{passed} passed, {failed} failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
