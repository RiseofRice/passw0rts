from setuptools import setup, find_packages

setup(
    name="passw0rts",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "cryptography>=41.0.7",
        "pyotp>=2.9.0",
        "click>=8.1.7",
        "rich>=13.7.0",
        "pyperclip>=1.8.2",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "pydantic>=2.5.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "passw0rts=passw0rts.cli:main",
        ],
    },
    author="RiseofRice",
    description="A secure cross-platform password manager with CLI and web UI",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/RiseofRice/passw0rts",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
)
