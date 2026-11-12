"""Opt-in regression isolation: keep fictional Lily/Mary, skip real-report seeding.

Use `-p tests.synthetic_seed_plugin`; not loaded in normal production or default tests.
No replacement real-report files are created. Report this fixture difference explicitly.
"""
def pytest_configure(config):
    import mcis_service.main as main
    main.seed_yangze22 = lambda *_args, **_kwargs: None
