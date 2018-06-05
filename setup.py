import setuptools

with open("readme.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="py-fpff",
    version="0.0.1",
    author="Jason Maa",
    description="Reads, writes, and exports FPFF files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jasmaa/py-fpff",
    packages=setuptools.find_packages(),
)
