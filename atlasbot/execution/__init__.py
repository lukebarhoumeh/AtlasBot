from atlasbot.config import EXECUTION_BACKEND


def get_backend(name: str | None = None):
    backend = name or EXECUTION_BACKEND
    if backend == "sim":
        from . import sim

        return sim
    if backend == "paper":
        from . import paper

        return paper
    raise ValueError(f"unknown backend {backend}")
