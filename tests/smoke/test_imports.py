import importlib

import pkg_resources


def test_imports():
    importlib.import_module("atlasbot")


def test_wheels():
    for p in ("pandas", "requests", "ccxt"):
        pkg_resources.get_distribution(p)
