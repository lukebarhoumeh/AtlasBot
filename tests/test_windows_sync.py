from atlasbot import run_logger as rl


def test_safe_sync_no_error():
    rl._safe_sync([])
