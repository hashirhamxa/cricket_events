# Cricbuzz Schedule & Data Reconnaissance Report

## 1. Executive Summary

This reconnaissance report outlines the investigation into Cricbuzz's web architecture, public data delivery mechanisms, schedule endpoints, match and team metadata representation, team asset CDN structures, timestamp encoding, failure points, and rate-limiting considerations.

The objective is to establish an automated, resilient, and non-intrusive scraping and normalization pipeline that produces clean, pre-processed JSON datasets and cached local assets for consumption by Android applications via raw GitHub URLs.

---

## 2. Investigated URLs & Endpoints

The following primary schedule and team URLs on Cricbuzz were investigated:

| Category / Resource | URL | Observed Status | Response Format |
|---|---|---|---|
| **All Upcoming** | `https://www.cricbuzz.com/cricket-schedule/upcoming-series/all` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **International** | `https://www.cricbuzz.com/cricket-schedule/upcoming-series/international` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **T20 Leagues** | `https://www.cricbuzz.com/cricket-schedule/upcoming-series/league` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **Domestic** | `https://www.cricbuzz.com/cricket-schedule/upcoming-series/domestic` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **Women** | `https://www.cricbuzz.com/cricket-schedule/upcoming-series/women` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **Team Directory (Intl)** | `https://www.cricbuzz.com/cricket-team` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **Team Directory (Domestic)**| `https://www.cricbuzz.com/cricket-team/domestic` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **Team Directory (League)** | `https://www.cricbuzz.com/cricket-team/league` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **Team Directory (Women)** | `https://www.cricbuzz.com/cricket-team/women` | 200 OK | Next.js Server Components HTML + RSC JSON |
| **Team Image CDN** | `https://static.cricbuzz.com/a/img/v1/0x0/i1/c{imageId}/i.jpg` | 200 OK | Image (JPEG/PNG, up to 640x480) |

> **Critical URL Note**: The T20 Leagues tab is routed on Cricbuzz as `/cricket-schedule/upcoming-series/league` rather than `t20-leagues`. Requesting `/t20-leagues` returns the generic layout without the schedule payload.

---

## 3. Data Delivery Architecture (Next.js React Server Components)

Cricbuzz's frontend is constructed with the **Next.js App Router**. Rather than rendering solely static HTML or relying on an unauthenticated REST API that could change or require authentication, Cricbuzz embeds hydration payloads directly into `<script>` chunks in the HTML body via:

```javascript
self.__next_f.push([1, "..."])
```

### 3.1 RSC Payload Structure

Inside one of the push chunks (identified by the presence of `matchScheduleMap`), the chunk string is a JSON-encoded string containing a component props object:

```json
{
  "scheduleData": {
    "matchScheduleMap": [
      {
        "scheduleAdWrapper": {
          "date": "MON, OCT 05 2026",
          "longDate": "1791158400000",
          "matchScheduleList": [
            {
              "seriesId": 13281,
              "seriesName": "Indonesia tour of South Korea, 2026",
              "seriesCategory": "International",
              "matchInfo": [
                {
                  "matchId": 174134,
                  "seriesId": 13281,
                  "matchDesc": "3rd T20I",
                  "matchFormat": "T20",
                  "startDate": "1791162000000",
                  "endDate": "1791244799000",
                  "team1": {
                    "teamId": 299,
                    "teamName": "South Korea",
                    "teamSName": "SKR",
                    "imageId": 172348
                  },
                  "team2": {
                    "teamId": 566,
                    "teamName": "Indonesia",
                    "teamSName": "IDN",
                    "imageId": 172618
                  },
                  "venueInfo": {
                    "ground": "Yeonhui Cricket Ground ",
                    "city": "Incheon",
                    "country": "South Korea ",
                    "timezone": "+09:00"
                  }
                }
              ]
            }
          ]
        }
      }
    ]
  }
}
```

---

## 4. Entity Extraction Strategy

### 4.1 Match Extraction
- **Match ID (`id` / `sourceMatchId`)**: Direct integer from `matchInfo.matchId` (e.g., `174134`).
- **Series ID (`seriesId`)**: Direct integer from `matchInfo.seriesId` or `matchScheduleList[].seriesId` (e.g., `13281`).
- **Series Name (`seriesName`)**: Direct string from `matchScheduleList[].seriesName`.
- **Match Description (`matchDesc`)**: E.g. `"3rd T20I"`, `"1st Match"`, `"Final"`, `"Pool A"`.
- **Match Format (`format`)**: Normalized uppercase string from `matchInfo.matchFormat` (`"T20"`, `"ODI"`, `"TEST"`).
- **Start Time (`startTime`)**: Integer milliseconds epoch from `matchInfo.startDate`.
- **UTC ISO Timestamp (`startTimeIso`)**: ISO-8601 formatted UTC string computed from epoch ms (`"2026-10-05T03:40:00Z"`).
- **Venue**: `venueInfo.ground` (stripped of trailing whitespace).
- **City**: `venueInfo.city`.
- **Country**: `venueInfo.country`.
- **Timezone**: `venueInfo.timezone`.

### 4.2 Team Extraction
- **Team ID**: Direct integer from `team1.teamId` / `team2.teamId`.
- **Team Name**: String from `team1.teamName` / `team2.teamName`.
- **Short Name**: String from `team1.teamSName` / `team2.teamSName` (e.g. `"IND"`, `"PAK"`, `"AUS"`, `"SKR"`).
- **Image ID**: Integer from `team1.imageId` / `team2.imageId`.

### 4.3 Series Extraction
- **Series ID**: Primary identifier.
- **Series Name**: Clean string title.
- **Category**: Derived from source tab and `seriesCategory` (`"INTERNATIONAL"`, `"T20_LEAGUE"`, `"DOMESTIC"`, `"WOMEN"`, `"OTHER"`).

---

## 5. Team Assets & Logo CDN

Cricbuzz serves high-resolution team logos via its static CDN:
- **Base Pattern**: `https://static.cricbuzz.com/a/img/v1/0x0/i1/c{imageId}/i.jpg`
- **Named Pattern**: `https://static.cricbuzz.com/a/img/v1/0x0/i1/c{imageId}/{slug}.jpg`

### Asset Caching Protocol:
1. When a new `teamId` is discovered with an `imageId`, our pipeline requests `https://static.cricbuzz.com/a/img/v1/0x0/i1/c{imageId}/i.jpg`.
2. The downloaded byte stream is inspected with **Pillow**:
   - Verify image validity (not HTML error page or 0-byte corrupt file).
   - Filter out 1x1 transparent placeholder GIFs.
   - Convert image to standard PNG format (`RGBA` / `RGB`).
3. Save to local repository path: `images/teams/{teamId}.png`.
4. Team object references the relative path: `"logo": "images/teams/{teamId}.png"`.
5. If already downloaded and valid, skip download to save bandwidth.

---

## 6. Failure Points & Fallback Strategies

| Potential Failure Point | Risk Level | Mitigation Strategy |
|---|---|---|
| Cricbuzz changes Next.js push format | Medium | Layered parsing: Regex JSON chunk decoder + balanced brace extractor + Fallback DOM parser parsing rendered HTML elements |
| Temporary network timeout / 5xx | Low | HTTP Retry strategy with exponential backoff (3 attempts, 2-8s backoff) |
| Scraping returns 0 matches (layout overhaul) | Critical | **Sanity Guard**: Validator checks count drop against previous run; aborts file replacement if drop exceeds sanity threshold |
| Image CDN 404 / 503 | Low | Keep existing cached image if present; log warning and set logo to `null` if unavailable |
| Timezone discrepancies | Low | Canonical timestamps stored as UTC epoch milliseconds and ISO-8601 UTC; localized files use explicit configurable timezone (`Asia/Karachi` by default) |

---

## 7. Rate-Limiting & Scraping Hygiene

1. Cricbuzz schedule pages do not require authentication or user cookies.
2. Standard desktop `User-Agent` and standard browser headers (`Accept`, `Accept-Language`) are supplied.
3. Total requests per scheduled run is tiny (~5 schedule pages + team directories + delta image downloads).
4. Delays of 0.5s–1.0s are injected between external requests.
5. GitHub Actions run on a scheduled 3–6 hour interval, remaining well below any rate thresholds.
