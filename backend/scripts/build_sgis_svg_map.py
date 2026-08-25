from __future__ import annotations

import argparse
import json
import math
import struct
import zipfile
from pathlib import Path
from typing import Iterable


SOURCE_URL = "https://www.data.go.kr/data/15129688/fileData.do"
SOURCE_TITLE = "국가데이터처_SGIS 행정구역 통계 및 경계_20250630"
REGION_ID_BY_CODE = {
    "11": "SEO",
    "21": "BUS",
    "22": "DGU",
    "23": "INC",
    "24": "GWJ",
    "25": "DJN",
    "26": "USN",
    "29": "SEJ",
    "31": "GYE",
    "32": "GAN",
    "33": "CBK",
    "34": "CNM",
    "35": "JBK",
    "36": "JNM",
    "37": "GBK",
    "38": "GNM",
    "39": "JEJ",
}
LABEL_POINT_OVERRIDES = {
    "SEO": (178.0, 184.0),
    "INC": (148.0, 219.0),
    "GYE": (219.0, 214.0),
    "SEJ": (193.0, 270.0),
    "CNM": (158.0, 302.0),
    "DJN": (218.0, 315.0),
    "GBK": (329.0, 300.0),
    "DGU": (298.0, 344.0),
    "GWJ": (154.0, 399.0),
    "JNM": (181.0, 438.0),
    "GNM": (274.0, 397.0),
    "BUS": (331.0, 417.0),
    "USN": (356.0, 371.0),
}


def archive_member(archive: zipfile.ZipFile, basename: str) -> str:
    matches = [name for name in archive.namelist() if Path(name).name == basename]
    if len(matches) != 1:
        raise RuntimeError(f"{basename}: expected one archive member, found {len(matches)}")
    return matches[0]


def decode_text(value: bytes, encoding: str) -> str:
    for candidate in (encoding, "utf-8-sig", "cp949", "euc-kr"):
        try:
            return value.decode(candidate).strip().strip("\x00")
        except UnicodeDecodeError:
            continue
    return value.decode("latin1").strip().strip("\x00")


def read_dbf(data: bytes, encoding: str) -> list[dict[str, str]]:
    record_count = struct.unpack_from("<I", data, 4)[0]
    header_length, record_length = struct.unpack_from("<HH", data, 8)
    fields: list[tuple[str, int]] = []
    offset = 32
    while offset + 32 <= header_length and data[offset] != 0x0D:
        descriptor = data[offset : offset + 32]
        name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        fields.append((name, descriptor[16]))
        offset += 32

    records = []
    for index in range(record_count):
        start = header_length + index * record_length
        record = data[start : start + record_length]
        if len(record) != record_length or record[:1] == b"*":
            continue
        cursor = 1
        row: dict[str, str] = {}
        for name, length in fields:
            row[name] = decode_text(record[cursor : cursor + length], encoding)
            cursor += length
        records.append(row)
    return records


def read_polygon_shapes(data: bytes) -> list[list[list[tuple[float, float]]]]:
    shapes: list[list[list[tuple[float, float]]]] = []
    offset = 100
    while offset + 8 <= len(data):
        _, content_words = struct.unpack_from(">II", data, offset)
        content_start = offset + 8
        content_end = content_start + content_words * 2
        if content_end > len(data):
            raise RuntimeError("SHP record extends beyond the source file")
        shape_type = struct.unpack_from("<I", data, content_start)[0]
        if shape_type == 0:
            shapes.append([])
            offset = content_end
            continue
        if shape_type not in {5, 15, 25}:
            raise RuntimeError(f"unsupported SHP polygon type: {shape_type}")
        num_parts, num_points = struct.unpack_from("<II", data, content_start + 36)
        parts_offset = content_start + 44
        part_starts = list(struct.unpack_from(f"<{num_parts}I", data, parts_offset))
        points_offset = parts_offset + num_parts * 4
        points = [
            struct.unpack_from("<dd", data, points_offset + index * 16)
            for index in range(num_points)
        ]
        rings = []
        for index, part_start in enumerate(part_starts):
            part_end = part_starts[index + 1] if index + 1 < len(part_starts) else num_points
            ring = points[part_start:part_end]
            if len(ring) >= 3:
                rings.append(ring)
        shapes.append(rings)
        offset = content_end
    return shapes


def perpendicular_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(dy * point[0] - dx * point[1] + end[0] * start[1] - end[1] * start[0]) / math.hypot(dx, dy)


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) <= 3:
        return points
    maximum, split = 0.0, 0
    for index in range(1, len(points) - 1):
        distance = perpendicular_distance(points[index], points[0], points[-1])
        if distance > maximum:
            maximum, split = distance, index
    if maximum <= tolerance:
        return [points[0], points[-1]]
    left = simplify(points[: split + 1], tolerance)
    right = simplify(points[split:], tolerance)
    return left[:-1] + right


def signed_area(points: list[tuple[float, float]]) -> float:
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    ) / 2


def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    area = signed_area(points)
    if abs(area) < 1:
        return (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
    factor = 1 / (6 * area)
    x = sum(
        (x1 + x2) * (x1 * y2 - x2 * y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    ) * factor
    y = sum(
        (y1 + y2) * (x1 * y2 - x2 * y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    ) * factor
    return x, y


def first_value(row: dict[str, str], candidates: Iterable[str]) -> str:
    for candidate in candidates:
        value = row.get(candidate, "").strip()
        if value:
            return value
    return ""


def build_map(zip_path: Path, tolerance: float, minimum_ring_area: float) -> dict:
    with zipfile.ZipFile(zip_path) as archive:
        basename = "bnd_sido_00_2025_2Q"
        shp = archive.read(archive_member(archive, f"{basename}.shp"))
        dbf = archive.read(archive_member(archive, f"{basename}.dbf"))
        cpg = decode_text(archive.read(archive_member(archive, f"{basename}.cpg")), "ascii") or "utf-8"
    rows = read_dbf(dbf, cpg)
    shapes = read_polygon_shapes(shp)
    if len(rows) != len(shapes):
        raise RuntimeError(f"DBF/SHP row mismatch: {len(rows)} != {len(shapes)}")

    regions = []
    for row, rings in zip(rows, shapes, strict=True):
        code = first_value(row, ("ADM_CD", "SIDO_CD", "CTPRVN_CD"))[:2]
        region_id = REGION_ID_BY_CODE.get(code)
        if not region_id:
            raise RuntimeError(f"unknown SGIS province code {code!r}; fields={row}")
        name = first_value(row, ("ADM_NM", "SIDO_NM", "CTP_KOR_NM"))
        kept = []
        for ring in rings:
            raw = ring[:-1] if ring[0] == ring[-1] else ring
            if len(raw) < 3 or abs(signed_area(raw)) < minimum_ring_area:
                continue
            simplified = simplify(raw, tolerance)
            if len(simplified) >= 3:
                kept.append(simplified)
        if not kept:
            raise RuntimeError(f"all rings were filtered for {name or code}")
        regions.append({"id": region_id, "code": code, "name": name, "rings": kept})

    all_points = [point for region in regions for ring in region["rings"] for point in ring]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    width, height, margin = 480.0, 680.0, 22.0
    scale = min((width - margin * 2) / (max_x - min_x), (height - margin * 2) / (max_y - min_y))
    offset_x = (width - (max_x - min_x) * scale) / 2
    offset_y = (height - (max_y - min_y) * scale) / 2

    def project(point: tuple[float, float]) -> tuple[float, float]:
        return (
            offset_x + (point[0] - min_x) * scale,
            offset_y + (max_y - point[1]) * scale,
        )

    locations = []
    for region in sorted(regions, key=lambda item: item["id"]):
        projected_rings = [[project(point) for point in ring] for ring in region["rings"]]
        path_parts = []
        for ring in projected_rings:
            first, *rest = ring
            path_parts.append(
                f"M{first[0]:.1f} {first[1]:.1f}"
                + "".join(f"L{point[0]:.1f} {point[1]:.1f}" for point in rest)
                + "Z"
            )
        largest = max(region["rings"], key=lambda ring: abs(signed_area(ring)))
        label_x, label_y = project(centroid(largest))
        label_x, label_y = LABEL_POINT_OVERRIDES.get(region["id"], (label_x, label_y))
        locations.append({
            "id": region["id"],
            "sgisCode": region["code"],
            "name": region["name"],
            "path": "".join(path_parts),
            "label": {"x": round(label_x, 1), "y": round(label_y, 1)},
        })
    return {
        "viewBox": "0 0 480 680",
        "source": SOURCE_TITLE,
        "sourceUrl": SOURCE_URL,
        "boundaryDate": "2025-06-30",
        "license": "이용허락범위 제한 없음",
        "locations": locations,
    }


def write_typescript(data: dict, target: Path) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "// Generated from the official SGIS 2025 Q2 province boundary dataset.\n"
        "// Regenerate with backend/scripts/build_sgis_svg_map.py; do not hand-edit paths.\n"
        f"export const SOUTH_KOREA_SGIS_MAP = {payload} as const;\n",
        encoding="utf-8",
    )


def write_svg(data: dict, target: Path) -> None:
    paths = "\n".join(
        f'  <path id="{item["id"]}" data-sgis-code="{item["sgisCode"]}" d="{item["path"]}"><title>{item["name"]}</title></path>'
        for item in data["locations"]
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{data["viewBox"]}">
  <metadata>{SOURCE_TITLE} · 2025-06-30 · 이용허락범위 제한 없음 · {SOURCE_URL}</metadata>
  <g fill="#b8d4f4" stroke="#ffffff" stroke-width="1.5" stroke-linejoin="round">
{paths}
  </g>
</svg>
''',
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_zip", type=Path)
    parser.add_argument("--typescript", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=250.0)
    parser.add_argument("--minimum-ring-area", type=float, default=1_000_000.0)
    args = parser.parse_args()
    data = build_map(args.source_zip, args.tolerance, args.minimum_ring_area)
    write_typescript(data, args.typescript)
    write_svg(data, args.svg)
    print(f"generated {len(data['locations'])} SGIS regions")


if __name__ == "__main__":
    main()
