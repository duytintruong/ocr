"""CLI to extract layout and split two-page newspaper images using AWS Textract."""

import json
from pathlib import Path

import boto3
import fire
import structlog
from PIL import Image, ImageDraw

logger = structlog.get_logger()

AWS_PROFILE = "dius"
AWS_REGION = "ap-southeast-2"


def extract_layouts(input_image: str, output_file: str) -> None:
    """Extract layout blocks from an image using AWS Textract and save to JSON.

    Args:
        input_image: Path to the input image file (JPEG or PNG).
        output_file: Path to the output JSON file to save Textract results.
    """
    image_path = Path(input_image)
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    log = logger.bind(input_image=str(image_path), output_file=output_file)
    log.info("reading_image")

    image_bytes = image_path.read_bytes()

    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    client = session.client("textract")

    log.info("calling_textract")
    response = client.analyze_document(
        Document={"Bytes": image_bytes},
        FeatureTypes=["LAYOUT"],
    )

    # Strip the raw response metadata that isn't serialisable
    response.pop("ResponseMetadata", None)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(response, indent=2, default=str))

    block_count = len(response.get("Blocks", []))
    log.info("layouts_saved", output_file=str(output_path), block_count=block_count)


def identify_split_line(input_image: str, layout_json: str, output_file: str) -> None:
    """Split a two-page newspaper image into two single-page images.

    Finds a vertical split line near the horizontal centre of the image that
    does not intersect any LAYOUT_* block from the Textract JSON, draws the
    line in red on a copy of the image and saves that annotated image.  The
    two cropped page halves are also saved alongside the annotated image, with
    ``_page1`` / ``_page2`` appended before the file extension of *output_file*.

    The search starts at the horizontal centre and moves outward in 10-pixel
    steps, alternating left and right, until a clear column gap is found.

    Args:
        input_image: Path to the two-page input image (JPEG or PNG).
        layout_json: Path to the Textract analyse-document JSON file.
        output_file: Path for the annotated output image (with the red line).
    """
    image_path = Path(input_image)
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    json_path = Path(layout_json)
    if not json_path.exists():
        raise FileNotFoundError(f"Layout JSON not found: {json_path}")

    log = logger.bind(input_image=str(image_path), layout_json=str(json_path))
    log.info("loading_image_and_layout")

    img = Image.open(image_path)
    img_width, img_height = img.size

    blocks = json.loads(json_path.read_text()).get("Blocks", [])
    layout_blocks = [b for b in blocks if b.get("BlockType", "").startswith("LAYOUT_")]

    # Convert each LAYOUT block bounding box to absolute pixel x-ranges.
    # Textract BoundingBox values are fractions of the image dimensions.
    block_x_ranges: list[tuple[float, float]] = []
    for block in layout_blocks:
        bb = block.get("Geometry", {}).get("BoundingBox", {})
        left_px = bb["Left"] * img_width
        right_px = (bb["Left"] + bb["Width"]) * img_width
        block_x_ranges.append((left_px, right_px))

    def _intersects(x: int) -> bool:
        return any(left <= x <= right for left, right in block_x_ranges)

    # Search outward from the centre in 10-pixel steps, alternating left/right.
    centre = img_width // 2
    split_x: int | None = None

    for offset in range(0, img_width // 2, 10):
        for candidate in ([centre] if offset == 0 else [centre - offset, centre + offset]):
            if 0 <= candidate <= img_width and not _intersects(candidate):
                split_x = candidate
                break
        if split_x is not None:
            break

    if split_x is None:
        raise RuntimeError("No clear vertical split line found in the image.")

    log.info("split_line_found", split_x=split_x, centre=centre, offset=abs(split_x - centre))

    # Draw the red split line on a copy of the image.
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)
    draw.line([(split_x, 0), (split_x, img_height - 1)], fill="red", width=3)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(output_path)
    log.info("annotated_image_saved", output_file=str(output_path))

    # Save the two cropped page halves.
    stem = output_path.stem
    suffix = output_path.suffix
    page1_path = output_path.with_name(f"{stem}_page1{suffix}")
    page2_path = output_path.with_name(f"{stem}_page2{suffix}")

    img.crop((0, 0, split_x, img_height)).save(page1_path)
    img.crop((split_x, 0, img_width, img_height)).save(page2_path)
    log.info("pages_saved", page1=str(page1_path), page2=str(page2_path))


def main() -> None:
    fire.Fire({"extract-layouts": extract_layouts, "identify-split-line": identify_split_line})


if __name__ == "__main__":
    main()
