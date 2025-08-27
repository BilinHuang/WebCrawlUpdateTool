import csv
import requests
import time
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import getpass

search_result = open('search_result.txt', 'w', newline='')

class LinkedInVerifier:
    def __init__(self):
        # Set up Chrome options
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--headless')  # Uncomment for headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

        self.differences = []
        self.updated_records = []
        self.logged_in = False

    def login_to_linkedin(self, username, password):
        """
        Log in to LinkedIn using Selenium
        """
        try:
            print("Logging in to LinkedIn...")
            self.driver.get('https://www.linkedin.com/login')

            # Wait for and fill username
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, 'username'))
            )
            username_field.send_keys(username)

            # Fill password
            password_field = self.driver.find_element(By.ID, 'password')
            password_field.send_keys(password)

            # Click login button
            login_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
            login_button.click()

            # Wait for login to complete (check for feed element)
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'artdeco-card'))
            )

            print("Login successful!")
            self.logged_in = True
            return True

        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def search_linkedin(self, name, company):
        """
        Search for a person on LinkedIn by name and company using Selenium
        Returns: profile URL if found, None otherwise
        """
        if not self.logged_in:
            print("Not logged in to LinkedIn. Please log in first.")
            return None

        search_query = f"{name},{company}"
        encoded_query = quote(search_query)
        url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_query}"

        try:
            print(f"Searching for: {name} at {company}")
            self.driver.get(url)

            # Wait for search results to load
            time.sleep(2)
            print("test point 1")

            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Look for profile results
            results = soup.find_all('div')

            mark = 0
            index = 0
            for result in results:
                if "Currently on the page 1 of" in result.text:
                    mark = 1
                if mark == 1:
                    for line in result.text.splitlines():
                        if "Current:" in line:
                            # Extract profile link
                            print("index:" , index , line,end="\n")
                            index = index + 1
                            search_result.write(result.text)


                    """
                    link_element = result.find('a', class_='app-aware-link')
                    if not link_element:
                        continue

                    profile_url = link_element.get('href')
                    if '/in/' in profile_url:
                        return profile_url.split('?')[0]  # Remove query parameters
                    """
            return None

        except Exception as e:
            print(f"Error searching for {name}: {str(e)}")
            return None

    def scrape_profile(self, profile_url):
        """
        Scrape LinkedIn profile information using Selenium
        Returns: dictionary with current_company, current_title, and contact_info if available
        """
        if not self.logged_in:
            print("Not logged in to LinkedIn. Please log in first.")
            return None

        try:
            print(f"Scraping profile: {profile_url}")
            self.driver.get(profile_url)

            # Wait for profile to load
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'pv-profile-section'))
            )

            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Extract current company and title
            profile_data = {}

            # Try to find current position
            experience_section = soup.find('section', {'id': 'experience'})
            if not experience_section:
                # Try alternative selectors
                experience_section = soup.find('div', {'id': 'experience-section'})

            if experience_section:
                # Find the most recent position
                current_position = experience_section.find('li', class_='artdeco-list__item')
                if not current_position:
                    # Try alternative selectors
                    current_position = experience_section.find('li', class_='pv-position-entity')

                if current_position:
                    company_element = current_position.find('span', class_='mr1')
                    if not company_element:
                        company_element = current_position.find('p', class_='pv-entity__secondary-title')

                    title_element = current_position.find('h3', class_='t-16')
                    if not title_element:
                        title_element = current_position.find('h3', class_='pv-entity__title')

                    if company_element:
                        profile_data['current_company'] = company_element.get_text(strip=True)
                    if title_element:
                        profile_data['current_title'] = title_element.get_text(strip=True)

            # Try to find contact info
            contact_info = self.extract_contact_info(soup)
            if contact_info:
                profile_data['contact_info'] = contact_info

            return profile_data

        except Exception as e:
            print(f"Error scraping profile: {str(e)}")
            return None

    def extract_contact_info(self, soup):
        """
        Try to extract contact information from the profile
        """
        # Look for the contact info link
        contact_link = soup.find('a', {'href': re.compile(r'/in/.*/contact-info')})
        if contact_link:
            contact_url = f"https://www.linkedin.com{contact_link['href']}"
            try:
                self.driver.get(contact_url)
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'ci-container'))
                )

                contact_page_source = self.driver.page_source
                contact_soup = BeautifulSoup(contact_page_source, 'html.parser')

                # Look for email
                email_section = contact_soup.find('section', {'class': 'ci-email'})
                if email_section:
                    email_element = email_section.find('a', href=re.compile(r'mailto:'))
                    if email_element:
                        return email_element.text.strip()

            except Exception as e:
                print(f"Error accessing contact info: {str(e)}")

        # Fallback: look for email in the "About" section
        about_section = soup.find('section', {'id': 'about'})
        if about_section:
            text = about_section.get_text()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            if emails:
                return emails[0]

        return None

    def verify_record(self, full_name, company, title, email):
        """
        Verify a single record against LinkedIn data
        """
        print(f"Verifying {full_name} from {company}...")

        # Search for the profile
        profile_url = self.search_linkedin(full_name, company)
        if not profile_url:
            print(f"  No profile found for {full_name}")
            self.differences.append({
                'name': full_name,
                'company': company,
                'title': title,
                'email': email,
                'issue': 'Profile not found',
                'profile_url': None
            })
            return None

        print(f"  Found profile: {profile_url}")

        # Scrape the profile
        profile_data = self.scrape_profile(profile_url)
        if not profile_data:
            print(f"  Could not scrape profile for {full_name}")
            self.differences.append({
                'name': full_name,
                'company': company,
                'title': title,
                'email': email,
                'issue': 'Could not scrape profile',
                'profile_url': profile_url
            })
            return None

        # Check for differences
        issues = []
        updated_record = {
            'name': full_name,
            'original_company': company,
            'original_title': title,
            'original_email': email,
            'profile_url': profile_url
        }

        # Check if still at the company
        current_company = profile_data.get('current_company', '')
        if current_company and company.lower() not in current_company.lower():
            issues.append(f"Company mismatch: expected {company}, found {current_company}")
            updated_record['current_company'] = current_company
        else:
            updated_record['current_company'] = company

        # Check if still in the same position
        current_title = profile_data.get('current_title', '')
        if current_title and title and title.lower() not in current_title.lower():
            issues.append(f"Title mismatch: expected {title}, found {current_title}")
            updated_record['current_title'] = current_title
        else:
            updated_record['current_title'] = title

        # Check for email updates
        contact_email = profile_data.get('contact_info', '')
        if contact_email and contact_email != email:
            issues.append(f"Email updated: from {email} to {contact_email}")
            updated_record['current_email'] = contact_email
        else:
            updated_record['current_email'] = email

        # Add to differences if there are issues
        if issues:
            self.differences.append({
                'name': full_name,
                'company': company,
                'title': title,
                'email': email,
                'issues': issues,
                'profile_url': profile_url
            })

        self.updated_records.append(updated_record)
        return updated_record

    def process_csv(self, filename):
        """
        Process the CSV file and verify all records
        """
        with open(filename, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Skip header row

            for row in reader:
                if len(row) < 4:
                    print(f"Skipping incomplete row: {row}")
                    continue

                full_name, company, title, email = row[0], row[1], row[2], row[3]
                self.verify_record(full_name, company, title, email)

                # Be respectful and add a delay between requests
                time.sleep(2)

    def generate_reports(self):
        """
        Generate reports for manual checking and updated database
        """
        # Create differences report
        with open('differences_report.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Name', 'Company', 'Title', 'Email', 'Issues', 'Profile URL'])

            for diff in self.differences:
                issues = diff.get('issues', [diff.get('issue', 'Unknown issue')])
                issues_str = '; '.join(issues) if isinstance(issues, list) else issues
                writer.writerow([
                    diff['name'],
                    diff['company'],
                    diff['title'],
                    diff['email'],
                    issues_str,
                    diff.get('profile_url', '')
                ])

        # Create updated database
        with open('updated_database.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'Name',
                'Original Company',
                'Current Company',
                'Original Title',
                'Current Title',
                'Original Email',
                'Current Email',
                'Profile URL'
            ])

            for record in self.updated_records:
                writer.writerow([
                    record['name'],
                    record['original_company'],
                    record.get('current_company', record['original_company']),
                    record['original_title'],
                    record.get('current_title', record['original_title']),
                    record['original_email'],
                    record.get('current_email', record['original_email']),
                    record['profile_url']
                ])

        print(f"Generated reports: {len(self.differences)} differences found")
        print("1. differences_report.csv - for manual checking")
        print("2. updated_database.csv - updated database for further processing")

    def close(self):
        """
        Close the browser
        """
        self.driver.quit()


# Main execution
if __name__ == "__main__":
    print("LinkedIn Profile Verification Tool")
    print("==================================")

    # Get LinkedIn credentials
    """
    username = input("Enter your LinkedIn username/email: ")
    password = input("Enter your LinkedIn password: ")
    """
    username = "bilinhuang5@gmail.com"
    password = "Billy060615"

    verifier = LinkedInVerifier()

    # Log in to LinkedIn
    if verifier.login_to_linkedin(username, password) or 1:
        # Process the CSV file
        verifier.process_csv('data.csv')
        verifier.generate_reports()
    else:
        print("Failed to log in to LinkedIn. Please check your credentials.")

    # Close the browser
    verifier.close()