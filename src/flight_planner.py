"""
Project 3 — Flight Route & Fare Comparator
Starter code (Python 3.11+)

You will:
- Parse flight schedule data from a plain-text or CSV file.
- Build a graph of airports and flights.
- Implement searches to find:
    * Earliest-arrival itinerary.
    * Cheapest itinerary in a given cabin (economy / business / first).
- Format a comparison table for the `compare` CLI command.

Everything marked TODO is your job.

Do not change function *names* or their parameters without updating tests.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional

# ---------------------------------------------------------------------------
# Constants & types
# ---------------------------------------------------------------------------

# You must honor this minimum layover between flights when searching.
MIN_LAYOVER_MINUTES: int = 60

Cabin = Literal["economy", "business", "first"]


@dataclass(frozen=True)
class Flight:
    """
    One scheduled flight (single day, same-day arrival).

    Times are stored as minutes since midnight (0–1439).
    """

    # TODO: verify you understand these fields and update docstrings as needed.
    origin: str
    dest: str
    flight_number: str
    depart: int  # minutes since midnight
    arrive: int  # minutes since midnight
    economy: int
    business: int
    first: int

    def price_for(self, cabin: Cabin) -> int:
        """
        Return the price for this flight in the given cabin.

        Hint:
        - Map cabin names to the numeric fields defined above.
        """
        if cabin == "economy":
            return self.economy
        elif cabin == "business":
            return self.business
        elif cabin == "first":
            return self.first
        else:
            raise ValueError(f"Unknown cabin: {cabin}")


@dataclass
class Itinerary:
    """
    A sequence of one or more flights representing a full journey.

    You should assume:
    - flights are in chronological order.
    - the destination of each flight matches the origin of the next.
    """

    flights: List[Flight]

    def is_empty(self) -> bool:
        return not self.flights

    @property
    def origin(self) -> Optional[str]:
        # TODO: return the origin airport code of the first flight, or None.
            if self.is_empty():
                return None
            return self.flights[0].origin

    @property
    def dest(self) -> Optional[str]:
        # TODO: return the destination airport code of the last flight, or None.
            if self.is_empty():
                return None
            return self.flights[-1].dest

    @property
    def depart_time(self) -> Optional[int]:
        # TODO: return the departure time (minutes) of the first flight, or None.
            if self.is_empty():
                return None
            return self.flights[0].depart

    @property
    def arrive_time(self) -> Optional[int]:
        # TODO: return the arrival time (minutes) of the last flight, or None.
            if self.is_empty():
                return None
            return self.flights[-1].arrive

    def total_price(self, cabin: Cabin) -> int:
        """
        Sum the price of all flights in this itinerary for the given cabin.
        """
        return sum(f.price_for(cabin) for f in self.flights)

    def num_stops(self) -> int:
        """
        Number of stops = flights - 1.

        Example:
        - 1 flight: 0 stops (direct).
        - 3 flights: 2 stops.
        """
        return max(0, len(self.flights) - 1)


# Graph type: adjacency list mapping airport code -> list of outgoing flights.
Graph = Dict[str, List[Flight]]

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def parse_time(hhmm: str) -> int:
    """
    Parse a time string 'HH:MM' (24-hour) into minutes since midnight.

    Examples:
        '00:00' -> 0
        '08:30' -> 510
        '23:59' -> 23*60 + 59

    TODO:
    - Split on ':'.
    - Convert hour and minute to ints.
    - Validate ranges (0 <= hour < 24, 0 <= minute < 60).
    - Return hour*60 + minute.
    """
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {hhmm}")
    hour, minute = parts
    hour = int(hour)
    minute = int(minute)
    if not (0 <= hour < 24) or not (0 <= minute < 60):
        raise ValueError(f"Hour or minute out of range: {hhmm}")
    return hour * 60 + minute


def format_time(minutes: int) -> str:
    """
    Convert minutes since midnight to 'HH:MM' (24-hour).

    Example:
        510 -> '08:30'

    TODO:
    - Compute hour = minutes // 60.
    - Compute minute = minutes % 60.
    - Use f-string formatting with zero padding: f\"{hour:02d}:{minute:02d}\".
    """
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


# ---------------------------------------------------------------------------
# Loading flights from files
# ---------------------------------------------------------------------------


def parse_flight_line_txt(line: str) -> Optional[Flight]:
    """
    Parse a single space-separated flight line.

    Format:
        ORIGIN DEST FLIGHT_NUMBER DEPART ARRIVE ECONOMY BUSINESS FIRST

    Behavior:
    - Return a Flight if the line contains data.
    - Return None for:
        * blank lines
        * comment lines starting with '#'
    - Raise ValueError for malformed data lines.

    TODO:
    - Strip the line.
    - If it's empty or startswith '#', return None.
    - Split on whitespace; expect exactly 8 fields.
    - Use parse_time() for DEPART and ARRIVE.
    - Convert prices to int.
    - Check that arrive > depart (same-day assumption).
    - Build and return a Flight.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    fields = line.split()
    if len(fields) != 8:
        raise ValueError(f"Malformed flight line: {line}")
    origin, dest, flight_number, depart, arrive, economy, business, first = fields
    depart_min = parse_time(depart)
    arrive_min = parse_time(arrive)
    if arrive_min <= depart_min:
        raise ValueError(f"Arrival time must be after departure: {line}")
    return Flight(
        origin=origin,
        dest=dest,
        flight_number=flight_number,
        depart=depart_min,
        arrive=arrive_min,
        economy=int(economy),
        business=int(business),
        first=int(first)
    )


def load_flights_txt(path: str) -> List[Flight]:
    """
    Load flights from a plain text schedule file.

    Lines:
        - Blank lines are ignored.
        - Lines starting with '#' are ignored.
        - Other lines must match the format parsed by parse_flight_line_txt().

    TODO:
    - Open the file.
    - Loop over lines with line numbers (enumerate).
    - Call parse_flight_line_txt on each.
    - If it returns a Flight, append it to a list.
    - If parse_flight_line_txt raises ValueError, re-raise with file/line info.
    """
    flights = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            try:
                flight = parse_flight_line_txt(line)
                if flight:
                    flights.append(flight)
            except ValueError as e:
                raise ValueError(f"{path}:{lineno}: {e}")
    return flights


def load_flights_csv(path: str) -> List[Flight]:
    """
    Load flights from a CSV file with header:

        origin,dest,flight_number,depart,arrive,economy,business,first

    TODO:
    - Use csv.DictReader.
    - Check that the required columns are present.
    - For each row:
        * parse depart/arrive with parse_time()
        * convert prices to int
        * check arrive > depart
        * build a Flight
    - Return the list of Flights.
    """
    required = ["origin", "dest", "flight_number", "depart", "arrive", "economy", "business", "first"]
    flights = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not all(col in reader.fieldnames for col in required):
            raise ValueError(f"Missing required columns in CSV: {reader.fieldnames}")
        for lineno, row in enumerate(reader, 2):
            try:
                depart_min = parse_time(row["depart"])
                arrive_min = parse_time(row["arrive"])
                if arrive_min <= depart_min:
                    raise ValueError(f"Arrival time must be after departure: {row}")
                flights.append(Flight(
                    origin=row["origin"],
                    dest=row["dest"],
                    flight_number=row["flight_number"],
                    depart=depart_min,
                    arrive=arrive_min,
                    economy=int(row["economy"]),
                    business=int(row["business"]),
                    first=int(row["first"])
                ))
            except Exception as e:
                raise ValueError(f"{path}:{lineno}: {e}")
    return flights


def load_flights(path: str) -> List[Flight]:
    """
    Wrapper that chooses TXT or CSV loader based on file extension.

    Rules:
    - If the extension (lowercased) is '.csv' → use load_flights_csv.
    - Otherwise → use load_flights_txt.

    TODO:
    - Inspect Path(path).suffix.
    - Call the appropriate loader and return the result.
    """
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        return load_flights_csv(path)
    else:
        return load_flights_txt(path)


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_graph(flights: Iterable[Flight]) -> Graph:
    """
    Build an adjacency-list graph from a collection of flights.

    graph[origin] = list of outgoing flights from that airport.

    TODO:
    - Create an empty dict mapping str -> list[Flight].
    - For each flight, append it to the list for its origin.
    - You can use dict.setdefault() or check membership manually.

    Complexity (for README later):
    - Time:  O(N) where N = number of flights.
    - Space: O(N) for the adjacency lists.
    """
    graph: Graph = {}
    for flight in flights:
        graph.setdefault(flight.origin, []).append(flight)
    return graph


# ---------------------------------------------------------------------------
# Search functions (earliest arrival / cheapest)
# ---------------------------------------------------------------------------


def find_earliest_itinerary(
    graph: Graph,
    start: str,
    dest: str,
    earliest_departure: int,
) -> Optional[Itinerary]:
    """
    Find an itinerary from `start` to `dest` that arrives as early as possible.

    Constraints:
    - First flight must depart at or after earliest_departure.
    - For each connection, the next flight must depart at or after
      (previous_arrival + MIN_LAYOVER_MINUTES).
    - All flights are same-day.

    Return:
    - Itinerary with >= 1 flight if a route exists.
    - None if no valid route exists.

    Hints:
    - Use a Dijkstra-like search where:
        * dist[airport] = earliest time you can be at that airport.
        * Priority queue stores (time, airport).
    - When relaxing edges (flights) from an airport:
        * Only consider flights where flight.depart >= current_time + MIN_LAYOVER_MINUTES
          (for the first leg, use earliest_departure instead of current_time).
    - Keep a `previous` dict to reconstruct the path (store the last Flight
      used to reach each airport).

    TODO:
    - Implement this search and return an Itinerary or None.
    """
    import heapq
    dist = {start: earliest_departure}
    prev = {}
    flight_taken = {}
    heap = [(earliest_departure, start)]
    while heap:
        curr_time, airport = heapq.heappop(heap)
        if airport == dest:
            # reconstruct path
            path = []
            a = dest
            while a != start:
                f = flight_taken[a]
                path.append(f)
                a = f.origin
            path.reverse()
            return Itinerary(path)
        for flight in graph.get(airport, []):
            min_depart = curr_time if airport == start else curr_time + MIN_LAYOVER_MINUTES
            if flight.depart >= min_depart:
                if (flight.dest not in dist) or (flight.arrive < dist[flight.dest]):
                    dist[flight.dest] = flight.arrive
                    flight_taken[flight.dest] = flight
                    heapq.heappush(heap, (flight.arrive, flight.dest))
    return None


def find_cheapest_itinerary(
    graph: Graph,
    start: str,
    dest: str,
    earliest_departure: int,
    cabin: Cabin,
) -> Optional[Itinerary]:
    """
    Find a valid itinerary from `start` to `dest` with the lowest total price
    in the given cabin, subject to the same timing & layover rules.

    Constraints (same as earliest-arrival):
    - First leg departs at or after earliest_departure.
    - Each connection respects MIN_LAYOVER_MINUTES.
    - All flights same-day.

    Return:
    - Itinerary if a route exists using that cabin for ALL legs.
    - None if no valid route exists.

    Hints:
    - You can still use a Dijkstra-style search, but:
        * dist[airport] = minimal total price to reach that airport.
    - When exploring edges:
        * Still enforce the time & layover rules.
        * Edge weight = flight.price_for(cabin).
    - Keep a `previous` dict to reconstruct the best path.

    TODO:
    - Implement this search and return an Itinerary or None.
    """
    import heapq
    dist = {start: 0}
    arr_time = {start: earliest_departure}
    prev = {}
    flight_taken = {}
    heap = [(0, earliest_departure, start)]  # (total_price, curr_time, airport)
    while heap:
        total_price, curr_time, airport = heapq.heappop(heap)
        if airport == dest:
            # reconstruct path
            path = []
            a = dest
            while a != start:
                f = flight_taken[a]
                path.append(f)
                a = f.origin
            path.reverse()
            return Itinerary(path)
        for flight in graph.get(airport, []):
            min_depart = curr_time if airport == start else curr_time + MIN_LAYOVER_MINUTES
            if flight.depart >= min_depart:
                price = total_price + flight.price_for(cabin)
                if (flight.dest not in dist) or (price < dist[flight.dest]):
                    dist[flight.dest] = price
                    arr_time[flight.dest] = flight.arrive
                    flight_taken[flight.dest] = flight
                    heapq.heappush(heap, (price, flight.arrive, flight.dest))
    return None


# ---------------------------------------------------------------------------
# Formatting the comparison table
# ---------------------------------------------------------------------------


@dataclass
class ComparisonRow:
    mode: str
    cabin: Optional[Cabin]  # e.g. None for earliest-arrival if you want
    itinerary: Optional[Itinerary]
    note: str = ""  # e.g. "(no valid itinerary)"


def format_comparison_table(
    origin: str,
    dest: str,
    earliest_departure: int,
    rows: List[ComparisonRow],
) -> str:
    """
    Format a text table comparing several itineraries.

    Required columns (at least):
        Mode, Cabin, Dep, Arr, Duration, Stops, Total Price

    Hints:
    - Convert times with format_time().
    - Duration = arrive_time - depart_time (then turn into HhMm string).
    - For missing itineraries (itinerary is None):
        * Use 'N/A' for most columns.
        * Include row.note in a final column or next to the row.

    TODO:
    - Build a list of text rows (strings).
    - Add a header line and a separator line.
    - Join them with '\\n' and return the final string.
    """
    header = ["Mode", "Cabin", "Origin", "Dest", "Dep", "Arr", "Duration", "Stops", "Total Price", "Note"]
    rows_out = []
    rows_out.append(" | ".join(header))
    rows_out.append("-|-".join(["-"*len(h) for h in header]))
    for row in rows:
        if row.itinerary is None:
            origin_val = dest_val = dep = arr = duration = stops = price = "N/A"
            note = row.note or "(no valid itinerary)"
        else:
            origin_val = row.itinerary.origin if row.itinerary.origin is not None else "N/A"
            dest_val = row.itinerary.dest if row.itinerary.dest is not None else "N/A"
            dep = format_time(row.itinerary.depart_time) if row.itinerary.depart_time is not None else "N/A"
            arr = format_time(row.itinerary.arrive_time) if row.itinerary.arrive_time is not None else "N/A"
            dur_min = (row.itinerary.arrive_time - row.itinerary.depart_time) if (row.itinerary.arrive_time is not None and row.itinerary.depart_time is not None) else None
            if dur_min is not None:
                h = dur_min // 60
                m = dur_min % 60
                duration = f"{h}h{m:02d}m"
            else:
                duration = "N/A"
            stops = str(row.itinerary.num_stops())
            price = str(row.itinerary.total_price(row.cabin)) if row.cabin else "N/A"
            note = row.note
        rows_out.append(f"{row.mode} | {row.cabin or 'N/A'} | {origin_val} | {dest_val} | {dep} | {arr} | {duration} | {stops} | {price} | {note}")
    return "\n".join(rows_out)


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def run_compare(args: argparse.Namespace) -> None:
    """
    Handle the 'compare' subcommand.

    Goal:
    - Read flights.
    - Build graph.
    - Run 4 searches:
        * Earliest arrival (time-based).
        * Cheapest economy.
        * Cheapest business.
        * Cheapest first.
    - Build ComparisonRow objects.
    - Print the formatted comparison table.

    TODO:
    - Parse earliest_departure using parse_time().
    - Call load_flights(args.flight_file).
    - Call build_graph(...) on the loaded flights.
    - Call find_earliest_itinerary(...) and find_cheapest_itinerary(...) 3 times.
    - Build a list[ComparisonRow] for these 4 results.
    - Call format_comparison_table(...) and print the string.
    """
    earliest_departure = parse_time(args.departure_time)
    flights = load_flights(args.flight_file)
    graph = build_graph(flights)
    earliest = find_earliest_itinerary(graph, args.origin, args.dest, earliest_departure)
    cheapest_economy = find_cheapest_itinerary(graph, args.origin, args.dest, earliest_departure, "economy")
    cheapest_business = find_cheapest_itinerary(graph, args.origin, args.dest, earliest_departure, "business")
    cheapest_first = find_cheapest_itinerary(graph, args.origin, args.dest, earliest_departure, "first")
    rows = [
        ComparisonRow(mode="Earliest Arrival", cabin=None, itinerary=earliest, note="" if earliest else "(no valid itinerary)"),
        ComparisonRow(mode="Cheapest", cabin="economy", itinerary=cheapest_economy, note="" if cheapest_economy else "(no valid itinerary)"),
        ComparisonRow(mode="Cheapest", cabin="business", itinerary=cheapest_business, note="" if cheapest_business else "(no valid itinerary)"),
        ComparisonRow(mode="Cheapest", cabin="first", itinerary=cheapest_first, note="" if cheapest_first else "(no valid itinerary)")
    ]
    table = format_comparison_table(args.origin, args.dest, earliest_departure, rows)
    print(table)


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build the top-level argument parser with a 'compare' subcommand.

    You generally do NOT need to change this unless you add features.
    """
    parser = argparse.ArgumentParser(
        description="FlyWise — Flight Route & Fare Comparator (Project 3)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare itineraries for a route (earliest arrival, cheapest per cabin).",
    )
    compare_parser.add_argument(
        "flight_file",
        help="Path to the flight schedule file (.txt or .csv).",
    )
    compare_parser.add_argument(
        "origin",
        help="Origin airport code (e.g., ICN).",
    )
    compare_parser.add_argument(
        "dest",
        help="Destination airport code (e.g., SFO).",
    )
    compare_parser.add_argument(
        "departure_time",
        help="Earliest allowed departure time (HH:MM, 24-hour).",
    )
    compare_parser.set_defaults(func=run_compare)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """
    Entry point for the CLI.

    Example usage:
        python flight_planner.py compare flights_global.txt ICN SFO 08:00
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# For your README (later) — Complexity checklist
# ---------------------------------------------------------------------------
# You will need to explain:
# - Building the graph:
#   - Time:   O(?)
#   - Space:  O(?)
#
# - Earliest-arrival search:
#   - Time:   O(?)
#   - Space:  O(?)
#
# - Cheapest-itinerary search:
#   - Time:   O(?)
#   - Space:  O(?)
#
# Replace ? with your Big-O reasoning in the README.
