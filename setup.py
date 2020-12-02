# Copyright 2020 Akamai Technologies, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import find_packages, setup

with open("README.md", "r") as fp:
    long_description = fp.read()


setup(
    name="dlock",
    version="0.1",
    author="Miloslav Pojman",
    author_email="mpojman@akamai.com",
    description="Locks your Docker dependencies",
    license="Apache License 2.0",
    url="https://github.com/akamai/dlock",
    project_urls={
        "Source Code": "https://github.com/akamai/dlock",
    },
    long_description=long_description,
    long_description_content_type="text/markdown",
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
    entry_points={
        "console_scripts": [
            "dlock=dlock.cli:run",
        ]
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "Docker",
        "Dockerfile",
        "containers",
        "dependencies",
        "lock",
        "locking",
        "pinning",
        "security",
        "digest",
        "hash",
    ],
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Security",
        "Topic :: Software Development",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
