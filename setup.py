from setuptools import find_packages, setup

setup(
    name="atlasbot",
    version="0.3.0",
    packages=find_packages(),  # finds the inner atlasbot package
    python_requires=">=3.10",
)
