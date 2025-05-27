import asyncio
from playwright.async_api import async_playwright, Dialog, Error
import logging
import re  # Import re for regex
import time  # Import time for delays
import csv  # Import csv for CSV file writing
import os  # Import os for file operations

# Configure logging to a file
logging.basicConfig(filename='scraper.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

async def handle_dialog(dialog: Dialog):
    logging.info(f"Dialog type: {dialog.type}")
    logging.info(f"Dialog message: {dialog.message}")
    try:
        if dialog.type == "alert" or dialog.type == "confirm" or dialog.type == "prompt":
            await dialog.accept()
            logging.info(f"Accepted dialog: {dialog.message}")
        elif dialog.type == "beforeunload":
            await dialog.accept()
            logging.info(f"Accepted beforeunload dialog.")
        else:
            # For permission dialogs, accept if it's a location request
            if "location" in dialog.message.lower():
                await dialog.accept()
                logging.info(f"Accepted location permission dialog.")
            else:
                await dialog.dismiss()
            logging.info(f"Dismissed dialog: {dialog.message}")
    except Error as e:
        logging.error(f"Playwright error handling dialog: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred in dialog handler: {e}")

async def main():
    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set up dialog handler for pop-ups like location permission
            page.on("dialog", handle_dialog)

            logging.info("Navigating to the page...")
            await page.goto("https://rera.odisha.gov.in/projects/project-list", wait_until="networkidle", timeout=120000)
            logging.info(f"Successfully navigated to: {page.url}")

            # Wait for the "Projects Registered" heading to be visible
            logging.info("Waiting for 'Projects Registered' heading...")
            await page.wait_for_selector("text=Projects Registered", state="visible", timeout=120000)
            await page.wait_for_load_state('networkidle', timeout=120000)  # Ensure all network requests are idle
            logging.info("'Projects Registered' heading is visible. Page loaded successfully.")

            # --- Handle any potential overlay/modal that intercepts clicks ---
            try:
                ok_button_locator = page.locator(".swal2-container button:has-text('OK')")
                if await ok_button_locator.is_visible():
                    logging.info("SweetAlert2-like modal with 'OK' button detected. Attempting to click 'OK'.")
                    await ok_button_locator.click()
                    await ok_button_locator.wait_for(state="hidden")
                    logging.info("SweetAlert2-like modal dismissed by clicking 'OK'.")
                    await page.wait_for_timeout(10000)  # Add a longer delay to ensure the page is ready after modal dismissal
                else:
                    logging.info("No SweetAlert2-like modal with 'OK' button found. Proceeding immediately.")
            except Error:
                logging.info("No SweetAlert2-like modal with 'OK' button found or could not dismiss it within timeout.")
            except Exception as e:
                logging.warning(f"Error trying to dismiss modal by clicking 'OK': {e}")

            # Verification: Take a screenshot to confirm content is visible and no modal
            await page.screenshot(path="initial_page_no_modal.png")
            logging.info("Screenshot 'initial_page_no_modal.png' taken.")

            # --- Phase 2: Identifying Project List Information ---
            logging.info("Identifying project elements...")

            # Step 1: Collect the names of the top 6 projects on initial load
            await page.wait_for_selector("div.card h5", state="visible")
            all_cards = await page.locator("div.card").all()
            project_names = []
            for card in all_cards:
                h5s = await card.locator("h5").all()
                if not h5s:
                    continue
                name = (await h5s[0].text_content()).strip()
                if name and name.lower() != "filter":
                    project_names.append(name)
                if len(project_names) == 6:
                    break
            logging.info(f"Collected top 6 project names: {project_names}")

            project_data = []
            project_names_index = 0
            while len(project_data) < 6:
                if project_names_index >= len(project_names):
                    logging.info("Reached end of current project names list. Attempting to collect more.")
                    # Reload the project list page to get potentially more projects
                    await page.goto("https://rera.odisha.gov.in/projects/project-list", wait_until="networkidle", timeout=120000)
                    await page.wait_for_selector("text=Projects Registered", state="visible", timeout=120000)
                    await page.wait_for_load_state('networkidle', timeout=120000)
                    all_cards_new = await page.locator("div.card").all()
                    project_names_new = []
                    for card in all_cards_new:
                        h5s = await card.locator("h5").all()
                        if not h5s:
                            continue
                        name = (await h5s[0].text_content()).strip()
                        if name and name.lower() != "filter":
                            project_names_new.append(name)

                    if len(project_names_new) <= project_names_index:
                        logging.warning("No more new projects found on the page to process.")
                        break # Exit loop if no new projects are available

                    project_names.extend(project_names_new[project_names_index:])
                    logging.info(f"Extended project names list. New total: {len(project_names)}")


                project_name = project_names[project_names_index]
                logging.info(f"Processing project: {project_name} (Index: {project_names_index})")

                # Reload the project list page for a fresh DOM before clicking
                await page.goto("https://rera.odisha.gov.in/projects/project-list", wait_until="networkidle", timeout=120000)
                # Handle modal if it appears
                ok_button_locator = page.locator(".swal2-container button:has-text('OK')")
                try:
                    if await ok_button_locator.is_visible():
                        logging.info("Modal detected after reload. Attempting to click 'OK'.")
                        await ok_button_locator.click()
                        await ok_button_locator.wait_for(state="hidden")
                        logging.info("Modal dismissed after reload.")
                        await page.wait_for_timeout(2000)
                    else:
                        logging.info("No modal found after reload. Proceeding immediately.")
                except Exception:
                    logging.info("No modal found after reload. Proceeding immediately.")
                await page.wait_for_selector("text=Projects Registered", state="visible", timeout=120000)
                await page.wait_for_load_state('networkidle', timeout=120000)

                # Find the card with the matching project name
                cards = await page.locator("div.card").all()
                found = False
                for card in cards:
                    h5s = await card.locator("h5").all()
                    if not h5s:
                        continue
                    name = (await h5s[0].text_content()).strip()
                    if name == project_name:
                        view_details_btns = await card.locator("a.btn.btn-primary:has-text('View Details')").all()
                        if not view_details_btns:
                            continue
                        btn = view_details_btns[0]
                        try:
                            async with page.expect_navigation():
                                await btn.click()
                        except Exception as e:
                            logging.error(f"Navigation error after clicking View Details for {project_name}: {e}")
                            project_names_index += 1
                            found = True # Mark as found to move to next project_names_index
                            break # Move to the next project_names_index in the outer while loop
                        # Handle modal if it appears after navigation
                        ok_button_locator = page.locator(".swal2-container button:has-text('OK')")
                        try:
                            if await ok_button_locator.is_visible():
                                logging.info("Modal detected after navigating to detail page. Attempting to click 'OK'.")
                                await ok_button_locator.click()
                                await ok_button_locator.wait_for(state="hidden")
                                logging.info("Modal dismissed after navigating to detail page.")
                                await page.wait_for_timeout(2000)
                            else:
                                logging.info("No modal found after navigating to detail page. Proceeding immediately.")
                        except Exception:
                            logging.info("No modal found after navigating to detail page. Proceeding immediately.")

                        # --- Phase 3: Scraping Detail Pages ---
                        current_project_details = {}

                        # Wait for the Project Name strong tag to have content other than '--'
                        project_name_locator = page.locator("div.details-project:has-text('Project Name') strong")
                        await project_name_locator.wait_for(state="visible", timeout=30000)
                        # Wait for the Project Name strong tag to have content other than '--'
                        start_time = time.time()
                        while await project_name_locator.text_content() == '--' and (time.time() - start_time) < 60:
                            await asyncio.sleep(0.5)  # Wait for 500ms before retrying
                        project_name_text = await project_name_locator.text_content()
                        logging.info(f"Project Name text content: {project_name_text}")
                        current_project_details["Project Name"] = project_name_text

                        # Wait for the RERA Regd. No. strong tag to have content other than '--'
                        rera_regd_no_locator = page.locator("div.details-project:has-text('RERA Regd. No.') strong")
                        await rera_regd_no_locator.wait_for(state="visible", timeout=30000)
                        start_time = time.time()
                        while await rera_regd_no_locator.text_content() == '--' and (time.time() - start_time) < 60:
                            await asyncio.sleep(0.5)  # Wait for 500ms before retrying
                        rera_regd_no_text = await rera_regd_no_locator.text_content()
                        logging.info(f"RERA Regd. No. text content: {rera_regd_no_text}")
                        current_project_details["Rera Regd. No"] = rera_regd_no_text

                        logging.info(f"Extracted: Project Name - {current_project_details['Project Name']}, Rera Regd. No - {current_project_details['Rera Regd. No']}")

                        # Step 3.3: Navigate to "Promoter Details" Tab and Extract Data
                        promoter_details_tab = page.locator("a:has-text('Promoter Details')")
                        await promoter_details_tab.click()

                        # Wait for any loading spinner or 'please wait...' to disappear before extracting promoter details
                        # (common for Angular/JS apps)
                        spinner_locator = page.locator(".ngx-overlay, .ngx-foreground-spinner, .ngx-loading-text:has-text('please wait')")
                        try:
                            await spinner_locator.wait_for(state="hidden", timeout=40000)
                        except Exception:
                            pass  # If spinner not found, proceed

                        # Wait for the promoter details card body to be visible (robust selector)
                        promoter_card_body_locator = page.locator(
                            ".card-body:has(label:has-text('Company Name')), .card-body:has(label:has-text('Propietory Name'))"
                        )
                        await promoter_card_body_locator.wait_for(state="visible", timeout=40000)
                        logging.info("Promoter Details card body visible.")

                        # Get the HTML content of the promoter details section
                        promoter_details_html = await promoter_card_body_locator.inner_html()  # Get inner HTML
                        with open(f"promoter_details_html_project_{project_names_index+1}.html", "w", encoding="utf-8") as f:  # Save with project index
                            f.write(promoter_details_html)
                        logging.info(f"Saved promoter_details_html_project_{project_names_index+1}.html for inspection.")

                        # Promoter Name (Company Name or Propietory Name under Promoter Details Tab)
                        company_name_locator = promoter_card_body_locator.locator("div.ms-3:has-text('Company Name') strong")
                        propietory_name_locator = promoter_card_body_locator.locator("div.ms-3:has-text('Propietory Name') strong")
                        promoter_name_text = None
                        start_time = time.time()
                        while True:
                            if await company_name_locator.count() > 0:
                                text = await company_name_locator.first.text_content()
                                if text and text.strip() != '--':
                                    promoter_name_text = text
                                    break
                            if await propietory_name_locator.count() > 0:
                                text = await propietory_name_locator.first.text_content()
                                if text and text.strip() != '--':
                                    promoter_name_text = text
                                    break
                            if (await company_name_locator.count() == 0 and await propietory_name_locator.count() == 0):
                                promoter_name_text = '--'
                                break
                            if time.time() - start_time > 40:
                                if promoter_name_text is None:
                                    promoter_name_text = '--'
                                break
                            await asyncio.sleep(0.5)
                        logging.info(f"Promoter Name text content: {promoter_name_text}")
                        current_project_details["Promoter Name"] = promoter_name_text

                        # Address of the Promoter (Registered Office Address or Permanent Address under Promoter Details Tab)
                        registered_address_locator = promoter_card_body_locator.locator("div.ms-3:has-text('Registered Office Address') strong")
                        permanent_address_locator = promoter_card_body_locator.locator("div.ms-3:has-text('Permanent Address') strong")
                        address_text = None
                        start_time = time.time()
                        while True:
                            if await registered_address_locator.count() > 0:
                                text = await registered_address_locator.first.text_content()
                                if text and text.strip() != '--':
                                    address_text = text
                                    break
                            if await permanent_address_locator.count() > 0:
                                text = await permanent_address_locator.first.text_content()
                                if text and text.strip() != '--':
                                    address_text = text
                                    break
                            if (await registered_address_locator.count() == 0 and await permanent_address_locator.count() == 0):
                                address_text = '--'
                                break
                            if time.time() - start_time > 40:
                                if address_text is None:
                                    address_text = '--'
                                break
                            await asyncio.sleep(0.5)
                        logging.info(f"Address text content: {address_text}")
                        current_project_details["Address of the Promoter"] = address_text

                        # GST No. (defensive: check if present, wait for value)
                        gst_no_locator = promoter_card_body_locator.locator("div.ms-3:has-text('GST No.') strong")
                        gst_no_text = '--'
                        start_time = time.time()
                        while True:
                            if await gst_no_locator.count() > 0:
                                text = await gst_no_locator.first.text_content()
                                if text and text.strip() != '':
                                    gst_no_text = text
                                    break
                            if time.time() - start_time > 40:
                                break
                            await asyncio.sleep(0.5)
                        logging.info(f"GST No. text content: {gst_no_text}")
                        current_project_details["GST No."] = gst_no_text

                        promoter_name = promoter_name_text.strip() if promoter_name_text else "--"
                        address = address_text.strip() if address_text else "--"

                        if not promoter_name or not address:
                            logging.warning(f"Skipping project {project_name} because either Promoter Name or Address is blank.")
                        else:
                            current_project_details["Promoter Name"] = promoter_name
                            current_project_details["Address of the Promoter"] = address
                            logging.info(f"Extracted Promoter Details: {current_project_details['Promoter Name']}, {current_project_details['Address of the Promoter']}, {current_project_details['GST No.']}")
                            project_data.append(current_project_details)
                            logging.info(f"Successfully extracted data for project: {project_name}")

                        found = True
                        break # Exit inner loop after processing the found card

                if not found:
                    logging.warning(f"Project card for '{project_name}' not found on reload.")

                project_names_index += 1 # Move to the next project name in the list

            logging.info(f"Scraping complete. Collected data for {len(project_data)} projects.")
            logging.info(f"Collected Data: {project_data}")

            # Write results to CSV for easy viewing (overwrite if exists)
            csv_file = "projects_output.csv"
            if project_data:
                with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(project_data[0].keys()))
                    writer.writeheader()
                    writer.writerows(project_data)
                logging.info(f"Results written to {csv_file}")
            else:
                logging.info("No data to write to CSV.")

            # Delete HTML and PNG files after successful run
            files_to_delete = [
                f for f in os.listdir('.')
                if f.endswith('.html') or f.endswith('.png')
            ]
            for f in files_to_delete:
                try:
                    os.remove(f)
                    logging.info(f"Deleted file: {f}")
                except Exception as e:
                    logging.warning(f"Could not delete file {f}: {e}")

        except Error as e:
            logging.error(f"Playwright error during main execution: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during main execution: {e}")
        finally:
            if browser:
                await browser.close()
                logging.info("Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())
