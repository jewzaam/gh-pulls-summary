# filepath: /home/nmalik/source/gh-pulls-summary/setup.py
from setuptools import setup, find_packages

setup(
    name="gh-pulls-summary",
    version="1.0.0",
    description="A tool to fetch and summarize GitHub pull requests.",
    author="Naveen Malik",
    author_email="jewzaam@gmail.com",
    packages=find_packages(),
    install_requires=[
        "requests",
        "argcomplete",
    ],
    entry_points={
        "console_scripts": [
            "gh-pulls-summary=gh_pulls_summary:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPLv3 License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)