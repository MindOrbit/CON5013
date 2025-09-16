#!/usr/bin/env python3
"""
Con5013 - The Ultimate Flask Console Extension
A powerful, beautiful web console for Flask applications with real-time monitoring,
terminal interface, API discovery, and system logging.
"""

from setuptools import setup, find_packages
import os

def read_file(filename):
    """Read file contents."""
    with open(filename, "r", encoding="utf-8") as fh:
        return fh.read()

def read_requirements():
    """Read requirements from requirements.txt."""
    try:
        return [line.strip() for line in read_file("requirements.txt").split('\n') 
                if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return ["flask>=2.0.0", "psutil>=5.8.0", "requests>=2.25.0"]

setup(
    name="con5013",
    version="1.0.0",
    author="Con5013 Team",
    author_email="team@con5013.dev",
    description="The Ultimate Flask Console Extension - Monitor, Debug, and Control Your Flask Applications",
    long_description=read_file("README.md") if os.path.exists("README.md") else "Con5013 - The Ultimate Flask Console Extension",
    long_description_content_type="text/markdown",
    url="https://github.com/MindOrbit/CON5013",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Flask",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Debuggers",
        "Topic :: System :: Logging",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    include_package_data=True,
    package_data={
        "con5013": [
            "static/css/*.css",
            "static/js/*.js",
            "static/assets/*",
            "templates/*.html",
        ],
    },
    entry_points={
        "console_scripts": [
            "con5013=con5013.cli:main",
        ],
    },
    keywords="flask console monitoring debugging terminal api logging dashboard con5013 crawl4ai",
    project_urls={
        "Bug Reports": "https://github.com/MindOrbit/CON5013/issues",
        "Source": "https://github.com/MindOrbit/CON5013",
        "Documentation": "https://docs.con5013.dev",
        "Homepage": "https://con5013.dev",
    },
    extras_require={
        "crawl4ai": ["crawl4ai>=0.2.0"],
        "dev": ["pytest>=6.0", "black", "flake8", "mypy"],
        "full": ["websockets>=10.0", "redis>=4.0.0", "celery>=5.0.0"],
    },
)


