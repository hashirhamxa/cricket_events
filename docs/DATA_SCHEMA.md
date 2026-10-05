# Cricket Data Schema Documentation

Version: `schemaVersion: 1`

All output datasets conform to the canonical JSON schema detailed below. Data is optimized for mobile applications (Android / iOS) using Kotlin Multiplatform, Retrofit, Kotlinx Serialization, Gson, or Moshi.

---

## 1. Match Model (`NormalizedMatch`)

Files:
- `data/matches/today.json`
- `data/matches/tomorrow.json`
- `data/matches/upcoming.json`
- `data/matches/all.json`
- `data/matches/international.json`
- `data/matches/t20_leagues.json`
- `data/matches/domestic.json`
- `data/matches/women.json`

### Field Definitions

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `id` | `integer` | Yes | Unique match ID (matches Cricbuzz match ID) | `174134` |
| `source` | `string` | Yes | Source identifier | `"cricbuzz"` |
| `sourceMatchId` | `integer` | Yes | Match ID from source | `174134` |
| `seriesId` | `integer` | No | ID of the series / tournament (nullable) | `13281` |
| `seriesName` | `string` | Yes | Name of the series / tournament | `"Indonesia tour of South Korea, 2026"` |
| `category` | `string` | Yes | Tournament category (`INTERNATIONAL`, `T20_LEAGUE`, `DOMESTIC`, `WOMEN`, `OTHER`) | `"INTERNATIONAL"` |
| `matchDesc` | `string` | Yes | Match description / round | `"3rd T20I"` |
| `format` | `string` | Yes | Cricket format (`T20`, `ODI`, `TEST`, `OTHER`) | `"T20"` |
| `teamAId` | `integer` | Yes | ID of Team A (references `teams.json`) | `299` |
| `teamBId` | `integer` | Yes | ID of Team B (references `teams.json`) | `566` |
| `teamAName` | `string` | Yes | Denormalized display name of Team A | `"South Korea"` |
| `teamBName` | `string` | Yes | Denormalized display name of Team B | `"Indonesia"` |
| `teamAShort` | `string` | Yes | Short code of Team A | `"SKR"` |
| `teamBShort` | `string` | Yes | Short code of Team B | `"IDN"` |
| `teamALogo` | `string` | No | Relative repository path to Team A logo | `"images/teams/299.png"` |
| `teamBLogo` | `string` | No | Relative repository path to Team B logo | `"images/teams/566.png"` |
| `startTime` | `integer` | Yes | Match start epoch timestamp in milliseconds (UTC) | `1791162000000` |
| `startTimeUtc` | `string` | Yes | ISO-8601 UTC timestamp | `"2026-10-05T01:00:00Z"` |
| `endTime` | `integer` | No | Match end epoch timestamp in milliseconds (UTC) | `1791244799000` |
| `venueId` | `integer` | No | Venue ID (nullable if not provided by source) | `null` |
| `venue` | `string` | Yes | Ground / stadium name | `"Yeonhui Cricket Ground"` |
| `city` | `string` | Yes | Host city | `"Incheon"` |
| `country` | `string` | Yes | Host country | `"South Korea"` |
| `timezone` | `string` | Yes | Venue timezone offset | `"+09:00"` |
| `status` | `string` | Yes | Status (`UPCOMING`, `LIVE`, `COMPLETED`, `CANCELLED`, `POSTPONED`, `ABANDONED`, `UNKNOWN`) | `"UPCOMING"` |

### Sample JSON:
```json
{
  "id": 174134,
  "source": "cricbuzz",
  "sourceMatchId": 174134,
  "seriesId": 13281,
  "seriesName": "Indonesia tour of South Korea, 2026",
  "category": "INTERNATIONAL",
  "matchDesc": "3rd T20I",
  "format": "T20",
  "teamAId": 299,
  "teamBId": 566,
  "teamAName": "South Korea",
  "teamBName": "Indonesia",
  "teamAShort": "SKR",
  "teamBShort": "IDN",
  "teamALogo": "images/teams/299.png",
  "teamBLogo": "images/teams/566.png",
  "startTime": 1791162000000,
  "startTimeUtc": "2026-10-05T01:00:00Z",
  "endTime": 1791244799000,
  "venueId": null,
  "venue": "Yeonhui Cricket Ground",
  "city": "Incheon",
  "country": "South Korea",
  "timezone": "+09:00",
  "status": "UPCOMING"
}
```

---

## 2. Team Model (`NormalizedTeam`)

File: `data/teams/teams.json`

Keyed as a dictionary of string team ID -> team object:

```json
{
  "2": {
    "id": 2,
    "name": "India",
    "shortName": "IND",
    "country": "India",
    "category": "INTERNATIONAL",
    "imageId": 776162,
    "logo": "images/teams/2.png",
    "flag": "images/flags/india.png",
    "primaryColor": null,
    "secondaryColor": null
  },
  "10": {
    "id": 10,
    "name": "West Indies",
    "shortName": "WI",
    "country": "West Indies",
    "category": "INTERNATIONAL",
    "imageId": 776191,
    "logo": "images/teams/10.png",
    "flag": "images/flags/west-indies.png",
    "primaryColor": null,
    "secondaryColor": null
  }
}
```

---

## 3. Series Model (`NormalizedSeries`)

File: `data/series/series.json`

Keyed as a dictionary of string series ID -> series object:

```json
{
  "13281": {
    "id": 13281,
    "name": "Indonesia tour of South Korea, 2026",
    "category": "INTERNATIONAL",
    "matchCount": 4
  },
  "7572": {
    "id": 7572,
    "name": "ICC Cricket World Cup League Two 2023-27",
    "category": "INTERNATIONAL",
    "matchCount": 18
  }
}
```

---

## 4. Venue Model (`NormalizedVenue`)

File: `data/venues/venues.json`

Keyed as a dictionary of normalized venue key / name -> venue details:

```json
{
  "yeonhui_cricket_ground_incheon": {
    "name": "Yeonhui Cricket Ground",
    "city": "Incheon",
    "country": "South Korea",
    "timezone": "+09:00"
  },
  "grand_prairie_stadium_dallas": {
    "name": "Grand Prairie Stadium",
    "city": "Dallas",
    "country": "United States",
    "timezone": "-05:00"
  }
}
```

---

## 5. Dataset Index Model (`DatasetIndex`)

File: `data/index.json`

```json
{
  "updatedAt": "2026-10-05T03:45:00Z",
  "source": "cricbuzz",
  "schemaVersion": 1,
  "timezone": "Asia/Karachi",
  "stats": {
    "totalMatches": 61,
    "upcomingMatches": 61,
    "todayMatches": 8,
    "tomorrowMatches": 12,
    "internationalMatches": 29,
    "t20LeagueMatches": 16,
    "domesticMatches": 13,
    "womenMatches": 8,
    "totalTeams": 63,
    "totalSeries": 15,
    "totalVenues": 19
  }
}
```
