from setuptools import find_packages, setup

setup(
    name="dlock",
    version="0.0.dev",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.7",
    install_requires=["docker"],
    extras_require={
        "dev": [
            "black",
            "flake8",
            "isort",
            "mypy",
            "pytest",
        ]
    },
    zip_safe=False,
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "dlock=dlock.cli:run",
        ]
    },
)
