# Cricket Data Repository (`cricket-data-hash`)

A production-ready, automated Cricket Data Repository that scrapes, normalizes, validates, caches team branding assets, and publishes clean fixture datasets directly to GitHub.

Android and mobile applications consume raw JSON and PNG assets directly via HTTPS from GitHub without performing any client-side scraping or requiring third-party API keys.

---

## 1. Architecture Overview

```
+-------------------------------------------------------------+
|              Public Sources (Cricbuzz / CDN)                |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|     Scraper & Parser Engine (src/client.py & src/parser.py) |
|      • Primary: Next.js React Server Component JSON         |
|      • Fallback: BeautifulSoup DOM Card Extraction          |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|       Normalization Engine (src/normalizer.py)              |
|      • UTC ISO-8601 & Epoch Millisecond Timestamps          |
|      • Canonical Match, Team, Series, Venue Models          |
|      • Automatic Entity Deduplication                       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|       Asset Manager & Cache (src/images.py)                 |
|      • Concurrent Worker Pool for Logo Downloads            |
|      • Pillow Image Integrity & MIME Type Validation        |
|      • Standardized PNG Local Caching (images/teams/{id}.png)|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|       Validator & Sanity Gates (src/validator.py)           |
|      • Strict Entity & Timestamp Integrity Assertions       |
|      • Sanity Drop Thresholds (Anti-Destruction Safety)     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|       Atomic Dataset Publisher (src/storage.py)             |
|      • Staging -> Validation -> Atomic Commit               |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|        GitHub Actions CI/CD (.github/workflows/)            |
|      • Scheduled Execution (Every 4 Hours)                  |
|      • Automated Git Commits on Data Changes                |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|       Direct Mobile / Android App Consumption               |
|      • Raw GitHub URLs for JSON & Cached Team Logos         |
+-------------------------------------------------------------+
```

---

## 2. Generated Production Files

All datasets conform to `schemaVersion: 1` and are hosted in the `data/` and `images/` directories:

### Match Partitions (`data/matches/`)
- `upcoming.json`: All upcoming fixtures across all categories.
- `today.json`: Fixtures occurring today (evaluated in `Asia/Karachi` PKT timezone).
- `tomorrow.json`: Fixtures occurring tomorrow (evaluated in `Asia/Karachi` PKT timezone).
- `all.json`: Complete chronological dataset of all deduplicated fixtures.
- `international.json`: International fixtures (Bilateral tours, ICC events, World Cups).
- `t20_leagues.json`: T20 franchise tournaments (IPL, PSL, BBL, CPL, etc.).
- `domestic.json`: First-class and domestic competitions.
- `women.json`: Women's international and franchise fixtures.

### Metadata & Reference Entities
- `data/teams/teams.json`: Team catalog containing names, short codes, countries, and local logo paths.
- `data/series/series.json`: Tournament registry with match counts and categories.
- `data/venues/venues.json`: Ground and city directory with local timezone offsets.
- `data/index.json`: Repository index with `updatedAt`, `schemaVersion`, and dataset counts.

### Asset Cache (`images/`)
- `images/teams/{teamId}.png`: High-resolution, verified PNG logos for all teams.
- `images/flags/{country}.png`: Country flags for international teams.

---

## 3. Mobile / Android Consumption Guide

Android applications consume raw files directly from GitHub:

```text
https://raw.githubusercontent.com/<owner>/cricket-data-hash/main/data/matches/upcoming.json
https://raw.githubusercontent.com/<owner>/cricket-data-hash/main/data/matches/today.json
https://raw.githubusercontent.com/<owner>/cricket-data-hash/main/data/teams/teams.json
https://raw.githubusercontent.com/<owner>/cricket-data-hash/main/data/index.json
```

Team images are loaded via:

```text
https://raw.githubusercontent.com/<owner>/cricket-data-hash/main/images/teams/{teamId}.png
```

### Kotlin Data Models (`Kotlinx Serialization`)

```kotlin
import kotlinx.serialization.Serializable

@Serializable
data class MatchFixture(
    val id: Long,
    val source: String,
    val sourceMatchId: Long,
    val seriesId: Long? = null,
    val seriesName: String,
    val category: String,
    val matchDesc: String,
    val format: String,
    val teamAId: Long,
    val teamBId: Long,
    val teamAName: String,
    val teamBName: String,
    val teamAShort: String,
    val teamBShort: String,
    val teamALogo: String? = null,
    val teamBLogo: String? = null,
    val startTime: Long, // Epoch ms UTC
    val startTimeUtc: String, // ISO-8601 UTC
    val endTime: Long? = null,
    val venueId: Long? = null,
    val venue: String,
    val city: String? = null,
    val country: String? = null,
    val timezone: String? = null,
    val status: String
)

@Serializable
data class Team(
    val id: Long,
    val name: String,
    val shortName: String,
    val country: String? = null,
    val category: String? = null,
    val imageId: Long? = null,
    val logo: String? = null,
    val flag: String? = null
)
```

### Jetpack Compose UI Example (with Coil)

```kotlin
@Composable
fun MatchCard(match: MatchFixture, baseUrl: String) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = match.seriesName, style = MaterialTheme.typography.labelSmall)
            Text(text = "${match.matchDesc} • ${match.format}", style = MaterialTheme.typography.bodySmall)
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Team A
                Row(verticalAlignment = Alignment.CenterVertically) {
                    AsyncImage(
                        model = "$baseUrl/${match.teamALogo}",
                        contentDescription = match.teamAName,
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = match.teamAShort, fontWeight = FontWeight.Bold)
                }

                Text(text = "vs", color = Color.Gray)

                // Team B
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = match.teamBShort, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.width(8.dp))
                    AsyncImage(
                        model = "$baseUrl/${match.teamBLogo}",
                        contentDescription = match.teamBName,
                        modifier = Modifier.size(36.dp)
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            Text(text = "${match.venue}, ${match.city ?: ""}", style = MaterialTheme.typography.bodySmall)
        }
    }
}
```

---

## 4. Local Execution

### Prerequisites
- Python 3.11+
- Virtual environment recommended

### Installation
```bash
pip install -r requirements.txt
```

### Running the Complete Pipeline
```bash
python scripts/run_pipeline.py
```

### CLI Options
- `--debug`: Enable verbose debug logging.
- `--no-logos`: Skip downloading newly discovered team logos.
- `--no-team-dirs`: Skip scraping global team directory catalogs.

### Individual Utility Scripts
- Fetch raw schedule: `python scripts/fetch_schedule.py --category every`
- Fetch team directory: `python scripts/fetch_teams.py`
- Download team logos: `python scripts/download_team_logos.py`
- Validate existing datasets: `python scripts/validate.py`

---

## 5. Automated Testing

Run the full automated test suite:

```bash
python -m pytest -v
```

The test suite includes:
- **Parser tests**: Verifies RSC payload and DOM fallback extraction against static HTML fixtures.
- **Normalizer tests**: Verifies timestamp formatting, category mappings, and ID extractions.
- **Deduplication tests**: Asserts that duplicate match occurrences are collapsed and sorted chronologically.
- **Image validation tests**: Verifies rejection of corrupted payloads, HTML error strings, and 1x1 placeholder GIFs.
- **Validator tests**: Tests sanity threshold drop guards and integrity assertions.
- **End-to-End pipeline tests**: Tests the complete pipeline run with mocked clients.

---

## 6. Resilience & Safety Features

1. **Atomic Publishing**: All data is initially written to a staging directory (`data/_staging/`). Full validation is executed before files are committed to production.
2. **Sanity Drop Threshold**: If a scraper run extracts 0 or significantly fewer matches than the previous valid dataset (< 30%), the pipeline aborts before modifying production files.
3. **HTTP Retry & Exponential Backoff**: Uses `urllib3.util.Retry` for handling 429 and 5xx network anomalies.
4. **Offline Testability**: All tests run without internet access using offline mock fixtures.

---

## 7. Documentation Index

- [Reconnaissance Report](docs/RECON_REPORT.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Data Schema Specification](docs/DATA_SCHEMA.md)
- [Source & Platform Notes](docs/SOURCE_NOTES.md)
- [Source Parity Audit Report](docs/PARITY_REPORT.md)
