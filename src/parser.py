"""Parser for extracting structured cricket schedule and team data from Cricbuzz Next.js HTML payloads."""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CricbuzzParser:
    """Extracts schedule, match, series, and team objects from Cricbuzz HTML."""

    def __init__(self):
        self.decoder = json.JSONDecoder()

    def parse_schedule_html(self, html: str, category_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse raw HTML from a Cricbuzz schedule page and extract all match fixture dictionaries.
        Uses RSC payload as primary method, falling back to regex extraction and DOM parsing.
        """
        if not html:
            return []

        # 1. Primary: Next.js RSC Push Payload
        matches = self._extract_matches_from_rsc(html, category_hint)
        if matches:
            logger.info(f"Successfully extracted {len(matches)} matches via primary RSC parser")
            return matches

        # 2. Fallback A: Raw ScheduleData JSON search
        matches = self._extract_matches_from_raw_json_block(html, category_hint)
        if matches:
            logger.info(f"Successfully extracted {len(matches)} matches via JSON block fallback")
            return matches

        # 3. Fallback B: DOM HTML Card Parser
        matches = self._extract_matches_from_dom(html, category_hint)
        if matches:
            logger.warning(f"Extracted {len(matches)} matches via DOM fallback parser (RSC missing)")
            return matches

        logger.error("All extraction strategies returned 0 matches for schedule page")
        return []

    def _extract_matches_from_rsc(self, html: str, category_hint: Optional[str]) -> List[Dict[str, Any]]:
        """Extract match fixtures from Next.js self.__next_f.push scripts."""
        matches = []
        pattern = re.compile(r'self\.__next_f\.push\(\[(\d+),\s*("(?:[^"\\]|\\.)*")\]\)', re.DOTALL)
        push_chunks = pattern.findall(html)

        for _, raw_str in push_chunks:
            if "matchScheduleMap" not in raw_str:
                continue
            try:
                decoded_str = json.loads(raw_str)
                idx = decoded_str.find('{"scheduleData":')
                if idx != -1:
                    obj, _ = self.decoder.raw_decode(decoded_str[idx:])
                    schedule_data = obj.get("scheduleData", {})
                    extracted = self._flatten_schedule_data(schedule_data, category_hint)
                    if extracted:
                        matches.extend(extracted)
            except Exception as e:
                logger.debug(f"Failed to decode RSC chunk: {e}")

        return matches

    def _extract_matches_from_raw_json_block(self, html: str, category_hint: Optional[str]) -> List[Dict[str, Any]]:
        """Fallback scanner searching for raw scheduleData JSON inside the document."""
        idx = html.find('{"scheduleData":')
        if idx == -1:
            idx = html.find('"scheduleData":')
            if idx != -1:
                idx = html.rfind('{', 0, idx)

        if idx != -1:
            try:
                obj, _ = self.decoder.raw_decode(html[idx:])
                schedule_data = obj.get("scheduleData", obj)
                return self._flatten_schedule_data(schedule_data, category_hint)
            except Exception as e:
                logger.debug(f"Failed raw JSON block decode: {e}")

        return []

    def _flatten_schedule_data(self, schedule_data: Dict[str, Any], category_hint: Optional[str]) -> List[Dict[str, Any]]:
        """Traverse matchScheduleMap and collect flattened match dictionaries."""
        flattened = []
        match_schedule_map = schedule_data.get("matchScheduleMap", [])

        for day_entry in match_schedule_map:
            wrapper = day_entry.get("scheduleAdWrapper", {})
            date_str = wrapper.get("date")
            long_date = wrapper.get("longDate")
            match_schedule_list = wrapper.get("matchScheduleList", [])

            for series_entry in match_schedule_list:
                series_id = series_entry.get("seriesId")
                series_name = series_entry.get("seriesName")
                series_category = series_entry.get("seriesCategory") or category_hint

                for match in series_entry.get("matchInfo", []):
                    item = dict(match)
                    # Enrich with series and date context
                    item["seriesId"] = item.get("seriesId") or series_id
                    item["seriesName"] = item.get("seriesName") or series_name
                    item["seriesCategory"] = series_category or category_hint
                    item["dateHeader"] = date_str
                    item["longDate"] = long_date
                    flattened.append(item)

        return flattened

    def _extract_matches_from_dom(self, html: str, category_hint: Optional[str]) -> List[Dict[str, Any]]:
        """Fallback DOM parser using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        match_links = soup.find_all("a", href=re.compile(r"/(?:live-cricket-scores|cricket-scores)/(\d+)/([a-z0-9-]+)"))
        
        matches = []
        seen_ids = set()

        for a in match_links:
            href = a.get("href", "")
            m = re.search(r"/(?:live-cricket-scores|cricket-scores)/(\d+)/([a-z0-9-]+)", href)
            if not m:
                continue
            match_id = int(m.group(1))
            slug = m.group(2)
            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)

            # Parse slug if possible (e.g. ind-vs-wi-3rd-odi-west-indies-tour-of-india-2026)
            text = a.get_text(separator=" ").strip()
            matches.append({
                "matchId": match_id,
                "slug": slug,
                "text": text,
                "seriesCategory": category_hint,
                "matchDesc": text,
                "format": "T20" if "t20" in slug.lower() else ("ODI" if "odi" in slug.lower() else "TEST"),
            })

        return matches

    def parse_team_directory_html(self, html: str, category_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse raw HTML from a Cricbuzz team directory page."""
        if not html:
            return []

        pattern = re.compile(r'self\.__next_f\.push\(\[(\d+),\s*("(?:[^"\\]|\\.)*")\]\)', re.DOTALL)
        push_chunks = pattern.findall(html)

        teams = []
        for _, raw_str in push_chunks:
            if "teamsList" not in raw_str:
                continue
            try:
                decoded_str = json.loads(raw_str)
                idx = decoded_str.find('{"teamsList":')
                if idx != -1:
                    obj, _ = self.decoder.raw_decode(decoded_str[idx:])
                    teams_list = obj.get("teamsList", {})
                    for group_name, team_arr in teams_list.items():
                        for t in team_arr:
                            item = dict(t)
                            item["group"] = group_name
                            item["directoryCategory"] = category_hint
                            teams.append(item)
            except Exception as e:
                logger.debug(f"Failed to decode team RSC chunk: {e}")

        return teams
