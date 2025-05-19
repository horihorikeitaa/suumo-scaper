from setuptools import setup, find_packages

setup(
    name="suumo_scraper",
    version="0.1.0",
    description="A tool for scraping real estate data from SUUMO",
    author="",
    author_email="",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "requests==2.32.3",
        "beautifulsoup4==4.13.4",
        "gspread==6.2.1",
        "google-auth==2.40.1",
        "functions-framework==3.8.3",
        "google-auth-oauthlib==1.2.2",
    ],
    python_requires=">=3.11",
)
