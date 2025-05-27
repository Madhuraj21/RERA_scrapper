# RERA Odisha Project Scraper

This Python script scrapes the first 6 projects listed under the “Projects Registered” section of the [Odisha RERA Project List](https://rera.odisha.gov.in/projects/project-list). For each project, it extracts the following details from the project’s detail page:

- **Rera Regd. No**
- **Project Name**
- **Promoter Name** (Company Name or Propietory Name under Promoter Details Tab)
- **Address of the Promoter** (Registered Office Address or Permanent Address under Promoter Details Tab)
- **GST No**

The extracted data is saved to a CSV file (`projects_output.csv`) for easy viewing. The script is robust to pop-up modals, dynamic loading, and field label variations.

---

## Features

- Scrapes the first 6 unique projects from the RERA Odisha site.
- Handles SweetAlert2-like modals and dynamic/AJAX content.
- Waits for all data to load, including slow AJAX responses.
- Extracts promoter details for both companies and individuals.
- Outputs results to a clean CSV file.
- Cleans up temporary HTML and PNG files after each run.

---

## Requirements

- Python 3.7+
- [Playwright](https://playwright.dev/python/)

### Install dependencies

Open PowerShell in your project directory and run:

```powershell
pip install playwright
playwright install
```

---

## Usage

1. Clone this repository or download `scraper.py` to your local machine.
2. Open PowerShell in the project directory.
3. Run the script:

   ```powershell
   python scraper.py
   ```

4. After the script finishes, you will find:
   - `projects_output.csv` — The extracted project data.
   - `scraper.log` — Log file with detailed run information.

All temporary HTML and PNG files are automatically deleted after each run.

---

## Output

The output CSV file will contain columns:

- Project Name
- Rera Regd. No
- Promoter Name
- Address of the Promoter
- GST No

You can open this file in Excel or any spreadsheet tool.

---

## Notes

- The script is designed to be robust against changes in field labels and dynamic content loading.
- If a field is missing on the site, it will appear as `--` in the CSV.


---

## License

This project is provided for educational and demonstration purposes.

---

**Repository:** [https://github.com/Madhuraj21/RERA_scrapper](https://github.com/Madhuraj21/RERA_scrapper)
