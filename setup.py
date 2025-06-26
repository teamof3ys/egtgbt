from setuptools import setup, find_packages

setup(
    name="egtgbt",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "aiogram>=3.0",
        "python-dotenv",
        "jinja2",
    ],
)