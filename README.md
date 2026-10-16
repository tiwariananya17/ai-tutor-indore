# TutorMatch Indore - AI Home Tutor Finder

## Run on Windows (first time)
1. Install Python 3.9 or newer from https://www.python.org/downloads/ . On the first installer screen tick **"Add python.exe to PATH"**.
2. Unzip this folder anywhere (e.g. Desktop). Do not run it from inside the ZIP.
3. Double-click **start.bat**. The first run creates a private `venv` folder and downloads the packages (needs internet, about a minute).
4. Your browser opens http://127.0.0.1:8000 . If the page says it can't connect, wait 5 seconds and refresh.
5. To stop, close the black window. Next time just double-click start.bat again (data is kept in `tutor.db`).

Run the automated tests: double-click **run_tests.bat** (after start.bat has been run once).

## Logins (no predefined parent or tutor accounts)
| Role | How to get in |
|---|---|
| **Admin** | Username `admin`, password `TutorMatch@Admin26` (one fixed login). Change it by setting `ADMIN_USERNAME` / `ADMIN_PASSWORD` before starting; it is re-applied at every start. **Change it before anyone else can reach the site.** |
| **Parent** | Open *Parent Login*, choose **Sign up**, create your account, then log in with your email and password. |
| **New tutor** | Open *Tutor Login*, choose **Sign up** (3 steps). You get a **Tutor ID** such as `TM-T057`; log in with that ID or your email. |
| **Tutor already listed** (the 56 pre-loaded tutors, and tutors imported by the admin) | Each has a Tutor ID `TM-T001` to `TM-T056`. On first start the app writes one-time activation codes to `tutor_activation_codes.csv` (keep this file private). The tutor opens *Tutor Login*, **Activate**, enters Tutor ID + code + their email + a new password, then logs in normally. The admin can also issue a fresh code any time in Admin, Tutors table (also how a forgotten password is reset). A code works once. |

The 56 pre-loaded tutors are fictional sample profiles (marked DEMO); replace them with real tutors when you go live. Any old `@demo.com` accounts from earlier versions are removed on start.

## Pages each person sees
- **Visitor (not logged in):** Home, AI Tutor Agent, All Tutors, Tutor Login, Parent Login, Admin login.
- **Parent:** My Requests (requests, upcoming sessions, calendar files), AI Tutor Agent, Find Tutors, Messages, Shortlist. Login pages, Home and admin pages are not shown.
- **Tutor:** Dashboard, Requests, Availability, Profile, Messages only.
- **Messages (parents and tutors):** an inbox of conversations with a chat window, message times, and automatic refresh every few seconds. A parent starts a chat from a tutor's profile (Chat button); a tutor can reply once a parent has written. Errors (for example an expired login) now show a message instead of failing silently.
- **Admin:** Overview (analytics), Tutors (Tutor IDs, verify, activation codes), Import, Requests only.
The menu changes with the role, and opening a page that belongs to another role simply returns you to your own start page. This is a convenience for the interface; the server enforces the real permissions on every request.

## What you can do
- **Parents:** describe the need in plain English (class, subject, area, budget, experience, gender, days, "evening", "weekend", board). See ranked tutors with a plain-language reason for each score. Browse, filter, sort, shortlist, "Near me", chat, request a demo/tutor slot, cancel, see phone after acceptance, review after acceptance.
- **Tutors:** sign up, set bio/board/fee/phone, weekly availability, accept/reject/complete requests, reply to messages.
- **Admin:** verify tutors, import real tutors by CSV (`data/real_tutors_template.csv`), remove demo profiles, see all requests.

## Extra features
Compare up to 3 tutors side by side; tutor dashboard with request stats, profile-completeness meter and upcoming sessions; parent dashboard with upcoming sessions; **Add to calendar** (.ics file) for accepted sessions; admin analytics bars; FAQ on the home page.

## Going live with real tutors
List only tutors who agreed. Have them Sign up (or import their CSV row), click **Verify** in Admin, then **Remove demo profiles**.
Imported rows are validated; `verified` in a CSV is ignored (admins verify explicitly).

## Classes, subjects, streams, medium, board
Tutors teach any range inside Classes 1-12. Choices come from one list in the server (`/api/catalog`): boards CBSE, ICSE, MP Board; medium English, Hindi; subjects grouped for Classes 1-5, 6-10, and for Classes 11-12 by stream (Science, Commerce, Arts). A tutor who covers Class 11 or 12 must pick at least one stream. The 56 sample tutors now cover every class from 1 to 12 (at least 10 tutors per class), with boards, medium and Science, Commerce and Arts streams for Classes 11-12 (`data/upgrade_sample_data.py` made the upgrade; databases from earlier versions are backfilled automatically on start, only for sample tutors who have not edited their profile).

## How matching works
Hard filters: class range and subject. Then a fixed weighted score (subject 30, class 20, location 15, experience 15, budget 10, availability 5, qualification 5, plus small bonuses for board, medium, stream, verified, parent rating). Every point is explained from profile data. There is no LLM; parsing is rule-based, so unusual phrasing may be missed (the assistant then asks for the missing class/subject).

## Security notes
Salted PBKDF2 passwords, expiring sessions, login throttling, ownership checks by user id, booking validation (future date, tutor availability, no double booking), text sanitising, security headers, no API docs exposed, server binds to 127.0.0.1 only. Not included: HTTPS, email verification, password reset, a persistent session store. Use a reverse proxy with HTTPS before exposing it to the internet.
"Near me" uses **approximate** area centres, not exact addresses; your coordinates are used for one request and not stored.
