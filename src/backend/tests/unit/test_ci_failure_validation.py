def test_deliberate_failure_for_ci_validation():
    """Deliberate failure to validate CI merge gating per T019."""
    assert False, "Deliberate test failure for CI gating validation (T019)"
