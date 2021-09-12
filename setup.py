import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="CyroWebB",
    version="0.0.3",
    author="CyroCoders",
    author_email="pypi@cyrocoders.ml",
    description="Backend Framework To Go Together With CyroWebF Frontend Framework.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CyroCoders/CyroWebB",
    project_urls={
        "Bug Tracker": "https://github.com/CyroCoders/CyroWebB/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3",
    entry_points = {
        "console_scripts": [
            "CyroWebB = CyroWebB.Production.__init__:Run",
        ]
    },
    install_requires=[
        'Jinja2==2.11.2',
        'Brotli==1.0.9',
        'WebOb==1.8.7',
        'parse==1.19.0',
        'psutil==5.8.0'
    ]
)