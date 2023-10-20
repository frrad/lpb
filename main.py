# pyright:strict


from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from datetime import datetime
from typing import Generator, List, cast
import dataclasses
import json
import requests


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

    response = requests.get(base_url, params=params)
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


def relevant(row: Course) -> bool:
    if "toddler" not in row.class_name.lower():
        return False

    if row.location != "SB":
        return False

    start_after_time = datetime.strptime("3:45pm", "%I:%M%p").time()
    end_before_time = datetime.strptime("7:00pm", "%I:%M%p").time()

    return (
        row.start_time.time() > start_after_time
        and row.start_time.time() < end_before_time
    )


for course in filter(relevant, parse(get_page())):
    course_dict = dataclasses.asdict(course)
    # datetime doesn't serialize so just remove it
    del course_dict["start_time"]
    del course_dict["end_time"]

    print(json.dumps(course_dict, indent=2))
