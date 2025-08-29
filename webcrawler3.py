# V3.0
"""
in this version we assume we have a csv with 

full name, company name, job title, email(not supported, but we have this LOL)

we use name + company to search the user

then for the linkedin website, we take the first search answer as the target

then, we use the descrition directly under the name to decide the company name and title

we assume there are two format:
{
name at company
compant - name
}
Then we print the comparisiong result in terminal and output the file to compare.csv

"""
import csv
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Profile:
    def __init__(self, fullname, company_name, job_title, email):
        self.fullname = fullname
        self.company = company_name
        self.job_title = job_title
        self.email = email


def login_to_linkedin(username, password):
    """
    Log in to LinkedIn using Selenium
    """
    try:
        print("Logging in to LinkedIn...")
        driver = webdriver.Chrome(options=webdriver.ChromeOptions())
        driver.get('https://www.linkedin.com/login')

        # Wait for and fill username
        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, 'username'))
        )
        username_field.send_keys(username)

        # Fill password
        password_field = driver.find_element(By.ID, 'password')
        password_field.send_keys(password)

        # Click login button
        login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')
        login_button.click()

        # Wait for login to complete (check for feed element)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'artdeco-card'))
        )

        print("Login successful!")
        return driver

    except Exception as e:
        print(f"Login failed: {str(e)}")
        exit(1)

def search_linkedin(driver, name, company):
    search_query = f"{name},{company}"
    encoded_query = quote(search_query)
    url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_query}"

    answer = Profile(None, None, None, None)
    try:
        print(f"Searching for: {name} at {company}")
        driver.get(url)
        time.sleep(3)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Look for the current position line in search results

        name_mark = 0
        next_name_mark = 0
        job_company_mark = 0
        connection_count = 0
        end_mark = 0

        for text in soup.stripped_strings:



            if next_name_mark == 1:
                answer.fullname = text
                next_name_mark = 0

            if job_company_mark == 1:
                if " at " in text:
                    answer.job_title = text.split(" at ")[0]
                    answer.company = text.split(' at ')[1]
                elif " - " in text:
                    answer.job_title = text.split(" - ")[1]
                    answer.company = text.split(' - ')[0]

            if "Currently on the page 1 of 1 search result page" in text:
                name_mark = 1
                next_name_mark = 1

            if name_mark == 1 and "connection" in text:
                connection_count += 1
                if connection_count > 1:
                    job_company_mark = 1

            if end_mark == 1:
                return answer

            if name_mark * job_company_mark == 1:
                end_mark = 1

        print("No current position found in search results")
        return None

    except Exception as e:
        print(f"Error searching for {name}: {str(e)}")
        return None


def verify_record(driver, full_name, company, title, email):
    """
    Verify a single record against LinkedIn data
    """
    # print(f"Verifying {full_name} from {company}...")

    compare_file = open("compare.csv", "a")


    # Search for the profile
    answer = search_linkedin(driver, full_name, company)
    if (answer.company != company) or (answer.fullname != full_name) or (answer.job_title != title):
        print(f"visit https://www.linkedin.com/search/results/people/?keywords={full_name},{company}")

    if answer.fullname != full_name:
        print("Incompatible name:", full_name, ":", answer.fullname)
        compare_file.write(f"\"{full_name}\",\"{answer.fullname}\",")
    else:
        compare_file.write(f"\"{full_name}\",\"\",")

    if answer.company != company:
        print("Incompatible company:", company, ":", answer.company)
        compare_file.write(f"\"{company}\",\"{answer.company}\",")
    else:
        compare_file.write(f"\"{company}\",\"\",")

    if answer.job_title != title:
        print("Incompatible title:",title, ":", answer.job_title)
        compare_file.write(f"\"{title}\",\"{answer.job_title}\"\n")
    else:
        compare_file.write(f"\"{title}\",\"\"\n")


print("LinkedIn Profile Verification Tool")
print("==================================")

# Get LinkedIn credentials
username = input("Enter your LinkedIn username/email: ")
password = input("Enter your LinkedIn password: ")

compare_file = open("compare.csv", "w")
compare_file.write(f"\"Original name\",\"Searched name\",\"Original company\",\"Searched company\",\"Original job title\",\"Searched job title\"\n")
compare_file.close()


with open("data.csv", 'r', newline='', encoding='utf-8') as file:
    reader = csv.reader(file)
    headers = next(reader)  # Skip header row

    driver = login_to_linkedin(username, password)

    for row in reader:
        if len(row) < 4:
            print(f"Skipping incomplete row: {row}")
            continue

        full_name, company, title, email = row[0], row[1], row[2], row[3]
        verify_record(driver, full_name, company, title, email)

        # Be respectful and add a delay between requests
        time.sleep(2)
