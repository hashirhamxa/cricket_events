# Source Notes & Cricbuzz Nuances

## 1. URL Path Inconsistencies

1. **T20 League Slug**:
   - The public navigation link labeled "T20 Leagues" routes to `/cricket-schedule/upcoming-series/league`.
   - Accessing `/cricket-schedule/upcoming-series/t20-leagues` serves a skeleton page with no `scheduleData` payload.
   - Always request `/cricket-schedule/upcoming-series/league`.

2. **Team Directory Paths**:
   - International: `/cricket-team`
   - Domestic: `/cricket-team/domestic`
   - League: `/cricket-team/league`
   - Women: `/cricket-team/women`

## 2. Next.js React Server Components (RSC) Push Format

Cricbuzz uses React Server Components. Chunks are pushed into `self.__next_f` via JavaScript statements formatted as:
```javascript
self.__next_f.push([1, "<escaped_json_string>"])
```

### Parsing Considerations:
- The second element of the tuple is a JSON-encoded string.
- In Python, unescaping can be done via `json.loads(f'"{raw_chunk}"')` or standard JSON decoders.
- Inside the decoded string, RSC component trees are represented as nested arrays: `["$", "ComponentRef", key, { props }]`.
- `scheduleData` is located inside the props object of the schedule component and contains `matchScheduleMap`.
- `teamsList` is located inside the props object on the team pages.

## 3. Date and Time Representation

- `startDate` and `endDate` inside Cricbuzz `matchInfo` objects are millisecond epoch timestamps encoded as strings (e.g. `"1791162000000"`).
- `venueInfo.timezone` contains the venue's local UTC offset (e.g. `"+09:00"`, `"-05:00"`).
- `longDate` in `scheduleAdWrapper` is the date boundary in epoch ms for the match day header.
- **Rule**: The canonical dataset stores timestamps as UTC integers and UTC ISO-8601 strings. Android clients convert to user local time or PKT without loss of precision.

## 4. Image Delivery Nuances

- High-res images: `https://static.cricbuzz.com/a/img/v1/0x0/i1/c{imageId}/i.jpg`.
- Requesting fixed dimensions (e.g. `150x150`) occasionally returns `image/gif` 1x1 transparent placeholders for certain non-primary teams.
- Using `0x0` returns the genuine unscaled asset (PNG or JPEG).
- Images should always be decoded through Pillow, normalized to standard PNGs, and verified to be larger than 10x10 px.

## 5. Team ID & Naming Conventions

- National teams generally have low IDs (e.g. India = 2, Pakistan = 3, Australia = 4, Sri Lanka = 5, England = 9, West Indies = 10, Afghanistan = 96).
- Associate and domestic teams have IDs ranging from 100 to 2000+.
- Short names (`teamSName`) are uppercase (3-5 characters, e.g. `IND`, `PAK`, `ENGCH`, `USA`, `LIMPO`).
- For tournaments involving composite/exhibition teams (e.g. "World Championship of Legends"), team short names reflect the competition (e.g. `INDCH`, `SACH`, `WICH`).

## 6. Match Status Mapping

Cricbuzz schedule matches are initially upcoming fixtures. The normalizer maps match statuses into standard states:
- `UPCOMING`: Scheduled match not yet started.
- `LIVE`: Ongoing match.
- `COMPLETED`: Finished match.
- `ABANDONED`: Match abandoned without a ball bowled or no result.
- `CANCELLED`: Match officially cancelled.
- `POSTPONED`: Match postponed to a future date.
- `UNKNOWN`: Fallback status when indeterminate.
