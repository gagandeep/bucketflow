from setuptools import setup, find_packages
import os
import re

# Read the contents of the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read version from __init__.py using regex
with open(os.path.join("bucketflow", "__init__.py"), "r", encoding="utf-8") as f:
    init_content = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", init_content, re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string in __init__.py")

setup(
    name="bucketflow",
    version=version,
    author="Gagan (Innerkore)",
    author_email="gagan@innerkore.com",
    description="A Python library for rate limiting using the Token Bucket algorithm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/innerkore/bucketflow",
    project_urls={
        "Bug Tracker": "https://github.com/innerkore/bucketflow/issues",
        "Documentation": "https://github.com/innerkore/bucketflow#readme",
        "Source Code": "https://github.com/innerkore/bucketflow",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.6",
    install_requires=[],
    extras_require={
        "distributed": ["redis>=3.0.0"],
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=20.8b1",
            "flake8>=3.8.0",
            "mypy>=0.800",
        ],
    },
    keywords="rate-limiting token-bucket throttling api hierarchical-rate-limiting",
)