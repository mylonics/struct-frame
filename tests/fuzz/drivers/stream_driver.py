"""Python stream driver: stream_driver.py <profile> <stream.bin> <chunk> [system].

With ``system`` the reader delivers system frames (printed with msg_id + 65536) and a final
``-1 <cnt_system_frames> <cnt_system_rejected> <cnt_crc_failures> <cnt_seq_gaps>`` line follows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import corpus  # noqa: E402

profile, path, chunk = sys.argv[1], sys.argv[2], int(sys.argv[3])
system = len(sys.argv) > 4 and sys.argv[4] == "system"
sys.stdout.write(corpus.render(corpus.reference_decode(profile, Path(path).read_bytes(), chunk, system=system)))
