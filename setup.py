import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="octopus",
    version="0.3",
    author="Richard Ingham",
    description="Real-time laboratory automation and monitoring in Python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/richardingham/octopus",
    packages=['octopus', 'octopus.manufacturer', 'octopus.blocks'],
    install_requires=requirements,
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
