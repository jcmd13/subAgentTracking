from setuptools import find_packages, setup

setup(
    name="subagent-tracking",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "typer>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "subagent=subagent_cli.app:main",
        ]
    },
)
