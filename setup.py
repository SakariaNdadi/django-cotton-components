from pathlib import Path
import setuptools

VERSION = "0.1.0"
NAME = "django-cotton-components"

INSTALL_REQUIRES = [
    "django-cotton==1.2.1",
]

setuptools.setup(
    name=NAME,
    version=VERSION,
    description="A Django package with pre-built cotton-based UI components for rapid development",
    url="https://github.com/SakariaNdadi/cotton-components/",
    project_urls={
        "Source Code": "https://github.com/SakariaNdadi/cotton-components/",
    },
    author="Sakaria Ndadi",
    author_email="oipapi.ndadi@gmail.com",
    license="MIT",
    license_files=("LICENSE",),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=INSTALL_REQUIRES,
    packages=setuptools.find_packages(),
    long_description=Path("README.MD").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
)
