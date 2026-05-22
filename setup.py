from setuptools import setup, find_packages

setup(
    name="governance-os",
    version="0.1.0",
    description="Multi-agent DAO governance intelligence and strategy platform",
    author="ucell17",
    author_email="aripin171103@gmail.com",
    url="https://github.com/ucell17/governance-os",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.25.0",
        "web3>=6.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "textblob>=0.17.1",
        "aiohttp>=3.9.0",
    ],
    entry_points={
        "console_scripts": [
            "govos=main:cli",
        ],
    },
)
