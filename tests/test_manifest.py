import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_video_pipeline.manifest import load_manifest, plan_durations

EXAMPLE = Path(__file__).parent.parent / "examples" / "example_manifest.yaml"


class TestPlanDurations:
    def test_covers_target_with_minimal_waste(self):
        cases = {8: [8], 21: [5, 8, 8], 10: [10], 5: [5], 25: [5, 10, 10]}
        for target, expected in cases.items():
            durations = plan_durations(target)
            assert sum(durations) >= target
            assert durations == expected

    def test_never_exceeds_max_clips_unnecessarily(self):
        for target in range(5, 41):
            durations = plan_durations(target, max_clips=4)
            assert sum(durations) >= target
            assert all(d in (5, 8, 10) for d in durations)

    def test_deterministic(self):
        assert plan_durations(17) == plan_durations(17)


class TestManifest:
    def test_loads_bundled_example(self):
        manifest = load_manifest(EXAMPLE)
        assert manifest.title
        assert len(manifest.shots) == 2
        assert manifest.shots[0].id == "S1"
        assert manifest.aspect_ratio == "1280:720"
