from setuptools import find_packages, setup

setup(
    name="tap-adorbit",
    version="0.1.0",
    description="A Singer tap for Ad Orbit.",
    author="The Daily Upside",
    author_email="dev@thedailyupside.com",
    packages=find_packages(),
    install_requires=[
        "singer-sdk>=0.13.0",
        "requests>=2.25.1",
    ],
    entry_points={
        "console_scripts": [
            "tap-adorbit=tap_adorbit.tap:TapAdOrbit.cli",
        ],
    },
)
