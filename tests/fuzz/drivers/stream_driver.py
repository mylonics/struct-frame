"""Python stream driver: stream_driver.py <profile> <stream.bin> <chunk>."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import corpus  # noqa: E402

profile, path, chunk = sys.argv[1], sys.argv[2], int(sys.argv[3])
sys.stdout.write(corpus.render(corpus.reference_decode(profile, Path(path).read_bytes(), chunk)))
