import setuptools

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name="py-fpff",
    version="1.0.0",
    author="Jason Maa",
    description="Library for working with FPFF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jasmaa/py-fpff",
    py_modules=["py_fpff"],
    packages=setuptools.find_packages(exclude=["tests.*", "tests"]),
)
