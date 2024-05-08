from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from flask import Flask

app = Flask(__name__)


def main():
    uri = "mongodb+srv://admin:JKEw0feoZCxOE0LS@cluster0.m5iuzzq.mongodb.net/?retryWrites=true&w=majority" \
          "&appName=Cluster0"

    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))

    db = client["webstores"]
    collection = db["webstoreItems"]
    wishlist = db["webstoreWishList"]

    print("Webscraping!")
    options = Options()

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Chrome/83.0.4103.116')
    options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.get('https://groceries.aldi.co.uk/en-GB/Search?keywords=tomato')
    # accept cookies
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-accept-btn-handler']"))).click()
    print("Cookies accepted")

    wishlist_items = wishlist.find({})

    for wish_item in wishlist_items:
        keyword = wish_item["ingredientName"]
        category = wish_item["ingredientCategory"]
        webscrape_aldi(driver, keyword, category)


# Aldi - search for specific keyword
def webscrape_aldi(driver, keyword, category):
    print(f"Webscraping for {keyword}")
    driver.get('https://groceries.aldi.co.uk/en-GB/Search?keywords=' + keyword)

    # accept cookies
    # WebDriverWait(driver, 10).until(
    #    EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-accept-btn-handler']"))).click()
    # print("Cookies accepted")

    # wait until items load
    WebDriverWait(driver, 10).until(
        EC.visibility_of_all_elements_located((By.XPATH, "//a[@class='p text-default-font']")))

    there_are_more_pages = True
    while there_are_more_pages:
        # get length of results
        item_len = len(driver.find_elements(By.XPATH, "//a[@class='p text-default-font']"))
        print("len is " + str(item_len))
        if item_len == 36:
            print("There is a next page!")
            there_are_more_pages = True
        else:
            print("We are on the LAST page!")
            there_are_more_pages = False

        for i in range(item_len):
            print("iteration " + str(i))
            while True:
                try:
                    # get results
                    items = driver.find_elements(By.XPATH, "//a[@class='p text-default-font']")
                    # wait for i-th product to be clickable then click it
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(items[i])).click()
                    break
                except:
                    driver.refresh()

            # get details of i-th product
            while True:
                item_name = driver.find_element(By.XPATH, "//h1[@class='my-0']")
                try:
                    ActionChains(driver).move_to_element(item_name).perform()
                    item_name_text = item_name.text
                    print("Item name is " + item_name_text)
                    break
                except:
                    driver.refresh()

            while True:
                item_weight = driver.find_element(By.XPATH, "//span[@class='text-black-50 font-weight-bold']")
                try:
                    ActionChains(driver).move_to_element(item_weight).perform()
                    item_weight_text = item_weight.text
                    print("Item weight is " + item_weight_text)
                    # remove 4 x 415g ==> 415g
                    if "x" in item_weight_text:
                        item_weight_text = item_weight_text.split("x")[1]
                        print(f"removed x: {item_weight_text}")
                    # remove drained weight in parentheses
                    if "(" in item_weight_text:
                        item_weight_text = item_weight_text.split("(")[0].removesuffix(" ")
                        print(f"removed (: {item_weight_text}")
                    if item_weight_text.endswith("kg"):
                        real_unit = "g"
                        real_weight = int(item_weight_text.removesuffix("kg")) * 1000
                        print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("g"):
                        real_unit = "g"
                        real_weight = int(item_weight_text.removesuffix("g"))
                        print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("l"):
                        real_unit = "ml"
                        real_weight = int(item_weight_text.removesuffix("l")) * 1000
                        print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("pint"):
                        real_unit = "ml"
                        real_weight = int(item_weight_text.removesuffix("pint")) * 568.261485
                        print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("pints"):
                        real_unit = "ml"
                        real_weight = int(item_weight_text.removesuffix("pints")) * 568.261485
                        print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("Pack"):
                        real_unit = "pack"
                        real_weight = int(item_weight_text.removesuffix("Pack"))
                        print("Item weight is actually " + str(real_weight) + real_unit)
                    else:
                        real_unit = "ERROR"
                        item_weight = 0
                        print("Item weight is in DIFFERENT unit")
                    break
                except:
                    driver.refresh()

            while True:
                item_price = driver.find_element(By.XPATH, "//span[@class='product-price h4 m-0 font-weight-bold']")
                try:
                    ActionChains(driver).move_to_element(item_price).perform()
                    item_price_text = item_price.text
                    print("Item price is " + str(item_price_text))
                    if not item_price_text.startswith("£"):
                        item_price_text = "ERROR"
                        print("Price is NOT in pounds")
                    else:
                        item_price_in_pence = int(float(item_price_text[1:]) * 100)
                        print("Item price is actually " + str(item_price_in_pence))
                    break
                except:
                    driver.refresh()

            # insert to db
            # newDoc = {
            #    "ingredientTag": keyword,
            #    "ingredientCategory": category,
            #    "ingredientName": item_name_text,
            #    "storeName": "Aldi",
            #    "weight": real_weight,
            #    "unit": real_unit,
            #    "price": item_price_in_pence
            # }

            # collection.insert_one(newDoc)

            # navigate back to search results
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(driver.find_element(By.XPATH, "//a[@class='pull-left']"))).click()

        # navigate to the next page
        # while True:
        # try:
        ActionChains(driver).move_to_element(driver.find_element(By.XPATH, "//a[@title='Next']")).click().perform()
        # WebDriverWait(driver, 10).until(
        #    EC.element_to_be_clickable(driver.find_element(By.XPATH, "//a[@title='Next']"))).click()
        print("NEXT PAGE")
        # break
        # except:
        # driver.refresh()


# Send a ping to confirm a successful connection
# try:
# client.admin.command('ping')
# print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
# print(e)

if __name__ == "__main__":
    main()
