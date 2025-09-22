# pyright:strict
from __future__ import annotations


from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Generator, List, cast, TypedDict
import dataclasses
import json
import requests
import yaml


@dataclass
class Course:
    class_name: str
    location: str
    instructor: str
    session: str
    gender: str
    age: str
    open: str
    cat2: str
    cat3: str
    days: str
    times: str
    fee: str
    start_time: datetime
    end_time: datetime


def get_page() -> str:
    base_url = "https://app.jackrabbitclass.com/webregopeningsv2.asp"
    params = {
        "searchpage": "29750",
        "rvcol": "0",
        "rtcol": "2",
        "rc": "0,1,2,3",
        "hc": "0,11",
        "hcat1": "no",
        "oid": "531495",
        "filterClasses": "",
        "waitlistClasses": "",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(base_url, params=params, headers=headers)
    response.raise_for_status()
    return response.text


def parse_time_range(time_range_str: str):
    start_str, end_str = time_range_str.split("-")

    # Define the format for parsing the time strings
    time_format = "%I:%M%p"  # Example: 3:15pm

    # Parse the start and end times
    start_time = datetime.strptime(start_str.strip(), time_format)
    end_time = datetime.strptime(end_str.strip(), time_format)

    return start_time, end_time


def find_and_get_text(row: Tag, attribute: str) -> str:
    element = row.find("td", {"data-title": attribute})
    assert element is not None, f"Element with data-title '{attribute}' not found"
    text = element.get_text(strip=True)
    return text


def extract_course_data(row: Tag) -> Course:
    class_name_cell = row.find("th")
    assert class_name_cell is not None
    class_name_parts = [item.strip() for item in class_name_cell.stripped_strings]
    class_name = (
        class_name_parts[1] if len(class_name_parts) == 2 else class_name_parts[0]
    )

    location = find_and_get_text(row, "Location")
    instructor = find_and_get_text(row, "Instructor")
    session = find_and_get_text(row, "Session")
    gender = find_and_get_text(row, "Gender")
    age = find_and_get_text(row, "Age")
    open = find_and_get_text(row, "Open")
    cat2 = find_and_get_text(row, "Cat2")
    cat3 = find_and_get_text(row, "Cat3")
    days = find_and_get_text(row, "Days")
    times = find_and_get_text(row, "Times")
    fee = find_and_get_text(row, "Fee")

    start_time, end_time = parse_time_range(times)

    return Course(
        class_name,
        location,
        instructor,
        session,
        gender,
        age,
        open,
        cat2,
        cat3,
        days,
        times,
        fee,
        start_time,
        end_time,
    )


def parse(html: str) -> Generator[Course, None, None]:
    soup: BeautifulSoup = BeautifulSoup(html, "html.parser")
    table = cast(Tag, soup.find("table", id="table-1"))
    rows: List[Tag] = table.find("tbody").find_all("tr", class_="qweb-reg-openings-row")

    for row in rows:
        assert isinstance(row, Tag)
        yield extract_course_data(row)


class ClassRules(TypedDict, total=False):
    name_includes: List[str]
    location_equals: str


class ScheduleRules(TypedDict):
    # 12-hour strings like "5:00pm" (default format below)
    start_after: str
    end_before: str
    exclude_days: List[str]
    # optional override, default "%I:%M%p"
    time_format: str


class ConfigDict(TypedDict, total=False):
    class_rules: ClassRules
    instructors: List[str]  # lowercase in config for simplicity
    schedule: ScheduleRules


@dataclass(frozen=True)
class Config:
    name_includes: List[str]
    location_equals: str | None
    instructors: List[str]
    start_after: time
    end_before: time
    exclude_days: List[str]

    @staticmethod
    def from_yaml(path: str | Path) -> "Config":
        raw: ConfigDict = yaml.safe_load(Path(path).read_text())

        class_rules = raw.get("class_rules", {})
        schedule = raw.get("schedule", {})

        tfmt = schedule.get("time_format", "%I:%M%p")
        start_after = datetime.strptime(schedule["start_after"], tfmt).time()
        end_before = datetime.strptime(schedule["end_before"], tfmt).time()

        return Config(
            name_includes=[s.lower() for s in class_rules.get("name_includes", [])],
            location_equals=class_rules.get("location_equals"),
            instructors=[s.lower() for s in raw.get("instructors", [])],
            start_after=start_after,
            end_before=end_before,
            exclude_days=schedule.get("exclude_days", []),
        )


def relevant(row: Course, cfg: Config) -> bool:
    # class name checks (all tokens must be found)
    class_lc = row.class_name.lower()
    correct_class = all(token in class_lc for token in cfg.name_includes)

    # location (optional)
    good_location = True
    if cfg.location_equals is not None:
        good_location = row.location == cfg.location_equals

    # instructor (any allowed matches, case-insensitive)
    instr_lc = row.instructor.lower()
    good_instructor = any(name in instr_lc for name in cfg.instructors)

    # time window
    s_time = row.start_time.time()
    e_time = row.end_time.time()
    good_time = (s_time >= cfg.start_after) and (e_time <= cfg.end_before)

    # day not excluded
    good_day = row.days not in cfg.exclude_days

    return (
        correct_class and good_location and good_time and good_day and good_instructor
    )


def main():

    cfg = Config.from_yaml("course_rules.yaml")

    for course in parse(get_page()):
        if not relevant(course, cfg):
            continue

        course_dict = dataclasses.asdict(course)
        # datetime doesn't serialize so just remove it
        del course_dict["start_time"]
        del course_dict["end_time"]

        print(json.dumps(course_dict, indent=2))


if __name__ == "__main__":
    main()
