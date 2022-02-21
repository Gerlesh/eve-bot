import discord
from discord.ext import commands
import random
import requests
import time
from bs4 import BeautifulSoup
from rq import Queue
from worker import conn
ret = []


def get_url(position, location):
    '''Generate url from position and location'''
    template = 'https://www.indeed.com/jobs?q={}&l={}'
    position = position.replace(" ", "+")
    location = location.replace(" ", "+")
    url = template.format(position, location)
    return url


def get_jobs(job_title, location):
    '''Max returned number of jobs is 15 per page.'''
    global ret
    url = get_url(job_title, location)
    print(f"URL: {url}")
    response = requests.get(url)
    print(f"Responses: {response}")
    soup = BeautifulSoup(response.text, "html.parser")

    job_names = []
    for job_name in soup.find_all("h2", class_="jobTitle"):
        job_names.append(job_name.get_text())
    
    companies = []
    for company in soup.find_all("span", class_="companyName"):
        companies.append(company.get_text())
    
    locations = []
    for location in soup.find_all("div", class_="companyLocation"):
        locations.append(location.get_text())
    
    salaries = []
    for salary in soup.find_all("div", class_="attribute_snippet"):
        if salary.get_text().startswith("$"):
            salaries.append(salary.get_text())
        else:
            salaries.append("Unknown")
    
    links = []
    for link in soup.find_all("a", class_=lambda value: value and value.startswith("tapItem fs-unmask result"), href=True):
        link = link["href"]
        link = "https://indeed.com" + link
        links.append(link)
    
    ret = [job_names, companies, locations, salaries, links]


class JobScraper(commands.Cog):

    def __init__(self, client):  # References whatever is passed through the client from discord
        self.client = client
        self.q = Queue(connection=conn)

    @commands.command(aliases=["job", "find_job", "find_jobs", "get_job", "get_jobs"])
    async def jobs(self, ctx, *, query):
        '''Scrapes Indeed.com for jobs and returns them.
        The input format should be "eve jobs [job title], [job location], [num returned]
        e.g. eve jobs ai researcher, san francisco, 3'''

        key_terms = query.split(",")
        key_terms = [term.strip() for term in key_terms]
        if len(key_terms) == 3:
            num_jobs = key_terms[2]
        else:
            num_jobs = 15
        
        # ret = get_jobs(key_terms[0], key_terms[1])
        job = self.q.enqueue(get_jobs, key_terms[0], key_terms[1])

        await ctx.send("Here is what I found:")
        print(ret)
            
        for i in range(num_jobs):
            await ctx.send("```" +
                f"\nTitle: {ret[0][i]}" + 
                f"\nCompany: {ret[1][i]}" + 
                f"\nLocation: {ret[2][i]}" +
                f"\nSalary: {ret[3][i]}" + 
                f"\nLink: {ret[4][i]}" +
                "\n```")


def setup(client):
    client.add_cog(JobScraper(client))
