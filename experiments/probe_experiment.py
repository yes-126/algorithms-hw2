import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable


TABLE_CAPACITY = 4093
MIN_LOAD_FACTOR = 0.25
MAX_LOAD_FACTOR = 4.0
LOAD_FACTOR_STEP = 0.25
FAILURE_TRIALS = TABLE_CAPACITY
RANDOM_SEED = 2026

CSV_COLUMNS = (
    "target_load",
    "actual_load",
    "capacity",
    "entries",
    "success_measured",
    "success_theory",
    "failure_measured",
    "failure_theory",
)


@dataclass(frozen=True)
class ExperimentResult:
    target_load: float
    actual_load: float
    capacity: int
    entries: int
    success_average: float
    success_theory: float
    failure_average: float
    failure_theory: float


def _load_factors():
    count = int((MAX_LOAD_FACTOR - MIN_LOAD_FACTOR) / LOAD_FACTOR_STEP) + 1
    return tuple(
        MIN_LOAD_FACTOR + index * LOAD_FACTOR_STEP for index in range(count)
    )


def _random_url(generator):
    host = generator.getrandbits(64)
    path = generator.getrandbits(128)
    return f"https://{host:016x}.example/{path:032x}"


def run_experiment(
    load_factors=None,
    capacity=TABLE_CAPACITY,
    failure_trials=FAILURE_TRIALS,
    seed=RANDOM_SEED,
):
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise TypeError("capacity must be an integer")
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    if isinstance(failure_trials, bool) or not isinstance(failure_trials, int):
        raise TypeError("failure_trials must be an integer")
    if failure_trials <= 0:
        raise ValueError("failure_trials must be positive")

    if load_factors is None:
        load_factors = _load_factors()
    else:
        load_factors = tuple(load_factors)
    if not load_factors:
        raise ValueError("at least one load factor is required")
    for load_factor in load_factors:
        if isinstance(load_factor, bool) or not isinstance(
            load_factor, (int, float)
        ):
            raise TypeError("load factors must be numbers")
        if load_factor <= 0:
            raise ValueError("load factors must be positive")

    generator = random.Random(seed)
    results = []

    for target_load in load_factors:
        entries = int(target_load * capacity)
        if entries <= 0:
            raise ValueError("each load factor must produce at least one entry")

        table = HashTable(capacity=capacity, max_load=None)
        urls = []
        for value in range(entries):
            url = _random_url(generator)
            while table.get(url) is not None:
                url = _random_url(generator)
            table.put(url, value)
            urls.append(url)

        success_comparisons = 0
        for value, url in enumerate(urls):
            stored_value, comparisons = table.get_with_count(url)
            if stored_value != value:
                raise RuntimeError("successful lookup returned an unexpected value")
            success_comparisons += comparisons

        failure_comparisons = 0
        for _ in range(failure_trials):
            url = _random_url(generator)
            while table.get(url) is not None:
                url = _random_url(generator)
            value, comparisons = table.get_with_count(url)
            if value is not None:
                raise RuntimeError("failure lookup unexpectedly found a key")
            failure_comparisons += comparisons

        actual_load = entries / capacity
        results.append(
            ExperimentResult(
                target_load=float(target_load),
                actual_load=actual_load,
                capacity=capacity,
                entries=entries,
                success_average=success_comparisons / entries,
                success_theory=1 + actual_load / 2,
                failure_average=failure_comparisons / failure_trials,
                failure_theory=actual_load,
            )
        )

    return results


def write_results_csv(results, path):
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for result in results:
            writer.writerow(
                (
                    f"{result.target_load:.2f}",
                    f"{result.actual_load:.8f}",
                    result.capacity,
                    result.entries,
                    f"{result.success_average:.8f}",
                    f"{result.success_theory:.8f}",
                    f"{result.failure_average:.8f}",
                    f"{result.failure_theory:.8f}",
                )
            )


def print_results_table(results):
    headings = (
        "target alpha",
        "actual alpha",
        "success avg",
        "success theory",
        "failure avg",
        "failure theory",
    )
    rows = [
        (
            f"{result.target_load:.2f}",
            f"{result.actual_load:.4f}",
            f"{result.success_average:.4f}",
            f"{result.success_theory:.4f}",
            f"{result.failure_average:.4f}",
            f"{result.failure_theory:.4f}",
        )
        for result in results
    ]
    widths = [
        max(len(heading), *(len(row[index]) for row in rows))
        for index, heading in enumerate(headings)
    ]
    print(" | ".join(heading.ljust(widths[index]) for index, heading in enumerate(headings)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.rjust(widths[index]) for index, value in enumerate(row)))


def write_svg(results, path):
    width = 1000
    height = 620
    left = 90
    right = 40
    top = 70
    bottom = 90
    plot_width = width - left - right
    plot_height = height - top - bottom
    y_max = max(
        4.0,
        *(result.success_average for result in results),
        *(result.success_theory for result in results),
        *(result.failure_average for result in results),
        *(result.failure_theory for result in results),
    )
    y_max = math.ceil(y_max * 1.1)

    def x_position(load_factor):
        return left + load_factor / MAX_LOAD_FACTOR * plot_width

    def y_position(comparisons):
        return top + (y_max - comparisons) / y_max * plot_height

    series = (
        ("Success measured", "success_average", "#1769aa", ""),
        ("Success theory", "success_theory", "#1769aa", "8 5"),
        ("Failure measured", "failure_average", "#c43b3b", ""),
        ("Failure theory", "failure_theory", "#c43b3b", "8 5"),
    )
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Measured and theoretical chaining hash-table probes</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2:.0f}" y="32" text-anchor="middle" font-family="sans-serif" font-size="20">Chaining lookup comparisons: measured vs theory</text>',
    ]

    for tick in range(y_max + 1):
        y = y_position(tick)
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#dddddd"/>'
        )
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="sans-serif" font-size="12">{tick}</text>'
        )

    for tick in range(5):
        x = x_position(tick)
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_height}" stroke="#eeeeee"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 24}" text-anchor="middle" font-family="sans-serif" font-size="12">{tick}</text>'
        )

    lines.extend(
        (
            f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#333333"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#333333"/>',
            f'<text x="{left + plot_width / 2:.2f}" y="{height - 20}" text-anchor="middle" font-family="sans-serif" font-size="14">Load factor alpha (entries / buckets)</text>',
            f'<text x="24" y="{top + plot_height / 2:.2f}" transform="rotate(-90 24 {top + plot_height / 2:.2f})" text-anchor="middle" font-family="sans-serif" font-size="14">Average node comparisons</text>',
        )
    )

    for name, attribute, color, dash in series:
        points = " ".join(
            f"{x_position(result.actual_load):.2f},{y_position(getattr(result, attribute)):.2f}"
            for result in results
        )
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"{dash_attribute}/>'
        )
        for result in results:
            lines.append(
                f'<circle cx="{x_position(result.actual_load):.2f}" cy="{y_position(getattr(result, attribute)):.2f}" r="3" fill="{color}"/>'
            )

    legend_y = height - 57
    legend_positions = (left, left + 220, left + 455, left + 690)
    for (name, _, color, dash), x in zip(series, legend_positions):
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(
            f'<line x1="{x}" y1="{legend_y}" x2="{x + 28}" y2="{legend_y}" stroke="{color}" stroke-width="2.5"{dash_attribute}/>'
        )
        lines.append(
            f'<text x="{x + 35}" y="{legend_y + 5}" font-family="sans-serif" font-size="12">{name}</text>'
        )

    lines.append("</svg>")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    results = run_experiment()
    output_directory = Path(__file__).resolve().parent
    csv_path = output_directory / "results.csv"
    svg_path = output_directory / "probe_experiment.svg"
    write_results_csv(results, csv_path)
    write_svg(results, svg_path)
    print_results_table(results)
    print(f"\nCSV: {csv_path}")
    print(f"SVG: {svg_path}")


if __name__ == "__main__":
    main()
