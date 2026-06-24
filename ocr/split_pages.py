"""CLI to extract layout blocks from an image using AWS Textract."""

import json
from pathlib import Path

import boto3
import fire
import structlog

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


def main() -> None:
    fire.Fire(extract_layouts)


if __name__ == "__main__":
    main()
