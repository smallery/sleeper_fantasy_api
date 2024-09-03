from setuptools import setup

setup(
    name="sleeper_fantasy_api",
    version="1.0.0",
    description="A Python wrapper for the Sleeper Fantasy API",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="Samuel Mallery",
    author_email="mallerysam@gmail.com",
    maintainer="Samuel Mallery",
    maintainer_email="mallerysam@gmail.com",
    url="https://github.com/smallery/sleeper_fantasy_api",
    install_requires=[
        # List dependencies here:
        "platformdirs==3.8.1",
        "requests==2.31.0"
    ],
    python_requires='>=3.10',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    zip_safe=False,
    keywords=['sleeper','fantasy football','football','nfl','sleeper api','fantasy']
)
