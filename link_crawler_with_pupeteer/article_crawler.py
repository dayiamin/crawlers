import asyncio
from pyppeteer import launch
import json
from lxml import html
import time
import os

"""
Web Scrapping with pupeteer in python
"""
current_folder = os.getcwd()
# loading the links
with open(rf'{current_folder}\files\combined_article_links.jsonl', 'r',encoding='utf-8') as json_file:
        json_content = json_file.readlines()
links = []
for content in json_content:
    links.append( json.loads(content).get('article_links'))

# loading previous saved slices
def read_slice():
    with open(rf'{current_folder}\files\article_slices_1.txt', 'r') as file:
            slices = json.loads(file.read())
    return (slices.get('start_slice'), slices.get('end_slice'))
start_slice, end_slice = read_slice()


start_urls = links[start_slice:end_slice]
# customize it
chrome_path = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'

def fix_names(authors):

    full_names = []
    temp_name = ''
    for name_part in authors:
        if name_part.strip(): 
            if temp_name: 
                full_name = f"{temp_name} {name_part}"
                full_names.append(full_name)
                temp_name = ''
            else:
                temp_name = name_part
    return full_names


# using pyppeteer to open the link in headless form
async def main(website):
    browser =await launch({"headless": True,
                            'executablePath':chrome_path
                            })
    page = await browser.newPage()
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    await page.setUserAgent(user_agent)

    for i in range(50):
        try:
            await page.goto(url = website,options={'timeout':2000000000})
            await page.waitFor(3000)
            page_content = await page.content()
            break
        except:
            print(f'Failed attempt {i}')   

    tree = html.fromstring(page_content)
    article_journal = tree.xpath('//meta[@name="citation_journal_title"]/@content')
    article_title = tree.xpath("//span[@class='title-text']/text()")
    article_authors = fix_names(tree.xpath("//span[@class='react-xocs-alternative-link']//text()"))
    article_doi = tree.xpath("//a[@class='anchor doi anchor-default']/@href")
    article_keywords = tree.xpath("//div[@class='keyword']//span/text()")
    article_abstract = tree.xpath("//div[@class='abstract author']/descendant::node()/text()")
    article_publish_date = tree.xpath('//meta[@name="citation_publication_date"]/@content')
    whole_references_text = {}
    try:
    #    getting type 1 reference from the website
        await page.waitForXPath('//li[@class="bib-reference u-margin-s-bottom"]',options={'timeout':8000})
        new_tree = html.fromstring(await page.content())
        references = new_tree.xpath('//li[@class="bib-reference u-margin-s-bottom"]')
        for index,ref in enumerate(references):
                whole_references_text[index] = ref.xpath('.//text()') 
        
        
    except:
        try:
                #    getting type 2 reference from the website
            print('type 1 ref was not there trying type 2')
            await page.waitForXPath('//span[@class="reference"]',options={'timeout':10000})
            new_tree = html.fromstring(await page.content())
            references = new_tree.xpath('//span[@class="reference"]')
            for index,ref in enumerate(references):
                whole_references_text[index] = ref.xpath('.//text()')
             
        except:
            print('no reference found')

        

    output_data = {
        'article_journal': article_journal,
        'article_title': article_title,
        'article_authors': article_authors,
        'article_doi': article_doi,
        'article_keywords': article_keywords,
        'article_abstract': article_abstract,
        'article_publish_date': article_publish_date,
        'references' :whole_references_text,


    }
    flag_status = False
    
    if article_title == [] and article_authors == [] and article_doi == []:
        # this check if the output was empty and usualy happens when you are blocked by website
        flag_status = True
        data = {'failed_article_links':website}
        with open(rf'{current_folder}\files\failed_artilce_links_1.jsonl', 'a') as file:
            for key, value in data.items():
                json_record = json.dumps({key: value})
                file.write(json_record + '\n')
    else:
        data = {'done_article_links':website}
        print(f'Saving article {article_title} to json file')
        with open(rf'{current_folder}\files\done_article_links_1.jsonl', 'a') as file:
            for key, value in data.items():
                json_record = json.dumps({key: value})
                file.write(json_record + '\n')
        with open(rf'{current_folder}\files\article_data_1.jsonl', 'a') as file: 
            json_record = json.dumps(output_data)
            file.write(json_record+ '\n')

    
    await browser.close()
    return flag_status


crawled_pages = 1
failure_counter = 0
start_time = time.time()
for link in start_urls:
    print(f'Crawling {link}')
    if failure_counter == 2:
        # depends on how long the website bans you
        print('Going into 3000 sec cooldown')
        failure_counter = 0
        time.sleep(3000)
    flag_status = asyncio.run(main(website=link))
    if flag_status:
        failure_counter += 1
    else:
        
        print(f"Crawling was successfull >> number of crawled pages = {crawled_pages}")
        with open(rf'{current_folder}\files\article_slices_1.txt', 'w') as file:
            file.write(json.dumps({'start_slice':crawled_pages+start_slice,
                                   'end_slice':end_slice}))
        crawled_pages +=1
    end_time = time.time()
    print(f'Average Crawl time is {(end_time-start_time)/crawled_pages}')
