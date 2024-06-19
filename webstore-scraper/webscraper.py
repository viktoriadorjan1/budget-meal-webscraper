from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from flask import Flask

app = Flask(__name__)

MAX_TRY = 5
MAX_WAIT = 30


def main():
    uri = "mongodb+srv://admin:JKEw0feoZCxOE0LS@cluster0.m5iuzzq.mongodb.net/?retryWrites=true&w=majority" \
          "&appName=Cluster0"

    # Create a new client and connect to the server
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
    except:
        print("ERROR: Could not connect to MongoDB")

    db = client["webstores"]
    collection = db["webstoreItems"]
    wishlist = db["webstoreWishList"]

    # delete entire db
    # collection.delete_many({})

    print("Webscraping!")
    options = Options()

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Chrome/83.0.4103.116')
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.get('https://groceries.aldi.co.uk/en-GB/Search?keywords=tomato')
    # accept cookies
    try_cookies = 0
    while try_cookies < MAX_TRY:
        try:
            WebDriverWait(driver, MAX_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-accept-btn-handler']"))).click()
            print("Cookies accepted")
            break
        except:
            driver.refresh()
            try_cookies = try_cookies + 1

    if try_cookies == MAX_TRY:
        print("ERROR: could not accept cookies")

    wishlist_items = wishlist.find({})
    # saving wishlist_items into separate list because Cursors can expire with time
    wishlist_items_saved = []

    #reached = False

    for wish_item in wishlist_items:
        wishlist_items_saved.append(wish_item)

    for wish_item in wishlist_items_saved:
        keyword = wish_item["ingredientName"]
        #if not reached:
            #if keyword != "cereal flakes":
                # skip until cereal flakes
                #continue
            #else:
                #reached = True
        category = wish_item["ingredientCategory"]
        possible_units = wish_item["possibleUnits"]
        unit_conversions = wish_item["unitConversions"]
        webscrape_aldi(driver, collection, keyword, category, possible_units, unit_conversions)

    driver.quit()


# Aldi - search for specific keyword
def webscrape_aldi(driver, collection, keyword, category, possible_units: list, unit_conversions):
    print(f"Webscraping for {keyword}")
    driver.get('https://groceries.aldi.co.uk/en-GB/Search?keywords=' + keyword)

    there_are_more_pages = True
    while there_are_more_pages:

        # wait until items load
        try:
            WebDriverWait(driver, MAX_WAIT).until(
                EC.visibility_of_all_elements_located((By.XPATH, "//a[@class='p text-default-font']")))
            # get length of results
            item_len = len(driver.find_elements(By.XPATH, "//a[@class='p text-default-font']"))
        except:
            print("Could not find any items")
            break

        # scan first page only
        there_are_more_pages = False

        # if item_len == 36:
        ## There is a next page!
        # there_are_more_pages = True
        # else:
        ## We are on the LAST page!
        # there_are_more_pages = False

        ## scrape fewer items
        # for i in range(item_len):
        #range_end = 3
        #if item_len < range_end:
            #range_end = item_len

        for i in range(item_len):
            print("iteration " + str(i) + " for " + keyword)
            try_item = 0
            while try_item < MAX_TRY:
                try:
                    # wait until items load
                    WebDriverWait(driver, MAX_WAIT).until(
                        EC.visibility_of_all_elements_located((By.XPATH, "//a[@class='p text-default-font']")))
                    # get results for item
                    items = driver.find_elements(By.XPATH, "//a[@class='p text-default-font']")
                    # save name of item
                    item_name_text = items[i].text

                    # save weight
                    weights = driver.find_elements(By.XPATH, "//div[@class='text-gray-small']")
                    item_weight_text = weights[i].text.lower()
                    # init real_unit
                    #real_unit = "ERROR"

                    # save price
                    price = driver.find_elements(By.XPATH, "//span[@class='h4']")
                    item_price_text = price[i].text
                    # init item_price_in_pence
                    # item_price_in_pence = "ERROR"

                    if not item_price_text.startswith("£"):
                        print(f"ERROR: {item_name_text} has price {item_price_text} which is NOT in pounds")
                    else:
                        item_price_in_pence = int(float(item_price_text[1:]) * 100)

                    # wait for i-th product to be clickable then click it
                    WebDriverWait(driver, MAX_WAIT).until(
                        EC.element_to_be_clickable(items[i])).click()
                    break
                except:
                    driver.refresh()
                    try_item = try_item + 1

            if try_item == MAX_TRY:
                print("ERROR: could not get item")
                continue

            # get details of i-th product
            #try_name = 0
            #while try_name < MAX_TRY:
            #    try:
                    # wait until name loads
            #        WebDriverWait(driver, MAX_WAIT).until(
            #            EC.visibility_of_element_located((By.XPATH, "//h1[@class='my-0']")))
            #        item_name = driver.find_element(By.XPATH, "//h1[@class='my-0']")

             #       ActionChains(driver).move_to_element(item_name).perform()
            #        item_name_text = item_name.text
                    # print("Item name is " + item_name_text)
            #        break
            #    except:
            #        driver.refresh()
            #        try_name = try_name + 1

            #if try_name == MAX_TRY:
            #    print("ERROR: could not get item name.")
                # navigate back to search results
            #    driver.back()
            #    continue
                #try:
                    # navigate back to search results
                #    WebDriverWait(driver, 60).until(
                #        EC.element_to_be_clickable(driver.find_element(By.XPATH, "//a[@class='pull-left']"))).click()
                #    continue
                #except:
                    #print("Could not navigate back to search results")
                    #break

            #print("Got name")


            # handle weight
            multiplier = 1
            if item_weight_text == "":
                print(f"ERROR: item weight was NOT given")
                driver.back()
                continue
            if "x" in item_weight_text:
                splitted = item_weight_text.split("x")
                try:
                    multiplier = float(splitted[0])
                except:
                    print(f"ERROR: multiplier {splitted[0]} is not a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
                item_weight_text = splitted[1]
            # remove drained weight in parentheses
            if "(" in item_weight_text:
                item_weight_text = item_weight_text.split("(")[0].removesuffix(" ")
            # remove text "typically"
            if item_weight_text.startswith("typically "):
                item_weight_text = item_weight_text.removeprefix("typically ")
            if item_weight_text.startswith("min "):
                item_weight_text = item_weight_text.removeprefix("min ")
            if item_weight_text.startswith("each"):
                real_weight = multiplier
                if ("grams" in possible_units) & (unit_conversions.get("grams") != 0):
                    real_unit = "g"
                    real_weight = real_weight * unit_conversions.get("grams")
                elif ("ml" in possible_units) & (unit_conversions.get("ml") != 0):
                    real_unit = "ml"
                    real_weight = real_weight * unit_conversions.get("ml")
                else:
                    print(f"{item_name_text} with weight {real_weight} (each) cannot be converted. Storing it as whole")
                try:
                    real_weight = float(real_weight) * multiplier
                    if unit_conversions.get("whole"):
                        real_unit = "whole"
                    else:
                        real_unit = "ERROR"
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue

            elif item_weight_text.endswith("kg"):
                real_unit = "g"
                real = item_weight_text.removesuffix("kg")
                try:
                    real_weight = float(real) * multiplier * 1000
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
            elif item_weight_text.endswith("g"):
                real_unit = "g"
                real = item_weight_text.removesuffix("g")
                try:
                    real_weight = float(real) * multiplier
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
            elif item_weight_text.endswith("ml"):
                real_unit = "ml"
                real = item_weight_text.removesuffix("ml")
                try:
                    real_weight = float(real) * multiplier
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
            elif item_weight_text.endswith("cl"):
                real_unit = "ml"
                real = item_weight_text.removesuffix("cl")
                try:
                    real_weight = float(real) * 10 * multiplier
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
            elif item_weight_text.endswith("l"):
                real_unit = "ml"
                real = item_weight_text.removesuffix("l")
                try:
                    real_weight = float(real) * 1000 * multiplier
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
            elif item_weight_text.endswith("pint"):
                real_unit = "ml"
                real = item_weight_text.removesuffix("pint")
                try:
                    real_weight = float(real) * 568.261485 * multiplier
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
            elif item_weight_text.endswith("pints"):
                real_unit = "ml"
                real = item_weight_text.removesuffix("pints")
                try:
                    real_weight = float(real) * 568.261485 * multiplier
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
            elif item_weight_text.endswith(" pack"):
                real = item_weight_text.removesuffix(" pack")
                if ("grams" in possible_units) & (unit_conversions.get("grams") != 0):
                    real_unit = "g"
                    try:
                        real = float(real) * unit_conversions.get("grams")
                    except:
                        print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                elif ("ml" in possible_units) & (unit_conversions.get("ml") != 0):
                    real_unit = "ml"
                    real = real * unit_conversions.get("ml")
                else:
                    print(f"{item_name_text} with weight {real} (pack) cannot be converted. Storing it as whole")
                try:
                    real_weight = float(real) * multiplier
                    if "whole" in possible_units:
                        real_unit = "whole"
                    else:
                        real_unit = "ERROR"
                except:
                    print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                    real_weight = "ERROR"
                    real_unit = "ERROR"
                    driver.back()
                    continue
                # print("Item weight is actually " + str(real_weight) + real_unit)
            else:
                print(f"ERROR: {item_name_text} has weight {multiplier} * {item_weight_text} which is a DIFFERENT "
                      f"unit")
                real_weight = "ERROR"
                real_unit = "ERROR"
                driver.back()
                continue


            """
            try_weight = 0
            while try_weight < MAX_TRY:
                try:
                    # wait until weight loads
                    WebDriverWait(driver, MAX_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, "//span[@class='text-black-50 font-weight-bold']")))
                    item_weight = driver.find_element(By.XPATH, "//span[@class='text-black-50 font-weight-bold']")

                    ActionChains(driver).move_to_element(item_weight).perform()
                    item_weight_text = item_weight.text.lower()
                    # print("Item weight is " + item_weight_text)
                    # save multiplier of 4 x 415g ==> later: 1660g
                    multiplier = 1
                    if "x" in item_weight_text:
                        splitted = item_weight_text.split("x")
                        try:
                            multiplier = float(splitted[0])
                        except:
                            print(f"ERROR: multiplier {splitted[0]} is not a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        item_weight_text = splitted[1]
                        # print(f"removed x: {item_weight_text}")
                    # remove drained weight in parentheses
                    if "(" in item_weight_text:
                        item_weight_text = item_weight_text.split("(")[0].removesuffix(" ")
                        # print(f"removed (: {item_weight_text}")
                    # remove text "typically"
                    if item_weight_text.startswith("Typically "):
                        item_weight_text = item_weight_text.removeprefix("Typically ")
                    if item_weight_text.startswith("each"):
                        real_weight = multiplier
                        if ("grams" in possible_units) & (unit_conversions["grams"] != 0):
                            real_unit = "g"
                            real_weight = real_weight * unit_conversions["grams"]
                        elif ("ml" in possible_units) & (unit_conversions["ml"] != 0):
                            real_unit = "ml"
                            real_weight = real_weight * unit_conversions["ml"]
                        else:
                            print(f"{item_name_text} with weight {real_weight} (each) cannot be converted")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("kg"):
                        real_unit = "g"
                        real = item_weight_text.removesuffix("kg")
                        # print(f"item_weight_text w/o suffix is {real}")
                        try:
                            real_weight = float(real) * multiplier * 1000
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("g"):
                        real_unit = "g"
                        real = item_weight_text.removesuffix("g")
                        try:
                            real_weight = float(real) * multiplier
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("ml"):
                        real_unit = "ml"
                        real = item_weight_text.removesuffix("ml")
                        try:
                            real_weight = float(real) * multiplier
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("l"):
                        real_unit = "ml"
                        real = item_weight_text.removesuffix("l")
                        try:
                            real_weight = float(real) * 1000 * multiplier
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("cl"):
                        real_unit = "ml"
                        real = item_weight_text.removesuffix("cl")
                        try:
                            real_weight = float(real) * 10 * multiplier
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                    elif item_weight_text.endswith("pint"):
                        real_unit = "ml"
                        real = item_weight_text.removesuffix("pint")
                        try:
                            real_weight = float(real) * 568.261485 * multiplier
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith("pints"):
                        real_unit = "ml"
                        real = item_weight_text.removesuffix("pints")
                        try:
                            real_weight = float(real) * 568.261485 * multiplier
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    elif item_weight_text.endswith(" pack"):
                        real = item_weight_text.removesuffix(" pack")
                        if ("grams" in possible_units) & (unit_conversions["grams"] != 0):
                            real_unit = "g"
                            real = float(real) * unit_conversions["grams"]
                            print(f"real: {real}")
                        elif ("ml" in possible_units) & (unit_conversions["ml"] != 0):
                            real_unit = "ml"
                            real = real * unit_conversions["ml"]
                        else:
                            print(f"{item_name_text} with weight {real} (pack) cannot be converted")
                        try:
                            real_weight = float(real) * multiplier
                        except:
                            print(f"ERROR: {item_name_text} with weight {multiplier} * {real} is NOT a float")
                            real_weight = "ERROR"
                            real_unit = "ERROR"
                            break
                        # print("Item weight is actually " + str(real_weight) + real_unit)
                    else:
                        print(f"ERROR: {item_name_text} has weight {multiplier} * {item_weight_text} which is a DIFFERENT "
                              f"unit")
                        real_weight = "ERROR"
                        real_unit = "ERROR"
                        break
                    break
                except:
                    driver.refresh()
                    try_weight = try_weight + 1

            if try_weight == MAX_TRY:
                print("ERROR: could not get item weight")
                # navigate back to search results
                driver.back()
                continue
                #try:
                    # navigate back to search results
                #    WebDriverWait(driver, 60).until(
                #        EC.element_to_be_clickable(driver.find_element(By.XPATH, "//a[@class='pull-left']"))).click()
                #    continue
                #except:
                    #print("Could not navigate back to search results")
                    #break

            print("Got weight")
            """

            """
            try_price = 0
            while try_price < MAX_TRY:
                try:
                    # wait until price loads
                    WebDriverWait(driver, MAX_WAIT).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//span[@class='product-price h4 m-0 font-weight-bold']")))
                    item_price = driver.find_element(By.XPATH, "//span[@class='product-price h4 m-0 font-weight-bold']")

                    ActionChains(driver).move_to_element(item_price).perform()
                    item_price_text = item_price.text
                    # print("Item price is " + str(item_price_text))
                    if not item_price_text.startswith("£"):
                        print(f"ERROR: {item_name_text} has price {item_price_text} which is NOT in pounds")
                    else:
                        item_price_in_pence = int(float(item_price_text[1:]) * 100)
                        # print("Item price is actually " + str(item_price_in_pence))
                    break
                except:
                    driver.refresh()
                    try_price = try_price + 1

            if try_price == MAX_TRY:
                print("ERROR: could not get item price")
                item_price_in_pence = "ERROR"
                # navigate back to search results
                driver.back()
                continue
                #try:
                    # navigate back to search results
                    #WebDriverWait(driver, 60).until(
                        #EC.element_to_be_clickable(driver.find_element(By.XPATH, "//a[@class='pull-left']"))).click()
                    #continue
                #except:
                    #print("Could not navigate back to search results")
                    #break

            print("Got price")
            """

            # get nutritional information

            nutrition_per = "UNSPECIFIED"
            energy = "UNSPECIFIED"
            fat = "UNSPECIFIED"
            saturates = "UNSPECIFIED"
            carbs = "UNSPECIFIED"
            sugars = "UNSPECIFIED"
            protein = "UNSPECIFIED"
            salt = "UNSPECIFIED"

            try_nutr = 0
            while try_nutr < MAX_TRY:
                try:
                    # wait until table loads
                    WebDriverWait(driver, MAX_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, "//table[@class='table table-striped']/tbody/tr")))

                    # nutritional information
                    specifications = driver.find_elements(By.XPATH, "//table[@class='table table-striped']/tbody/tr")

                    actual_rows = None

                    for row in specifications:
                        row_text = row.text
                        if "Nutrition information" in row_text:
                            actual_rows = row_text.split('\n')

                    if actual_rows is not None:
                        for row in actual_rows:
                            print(f"row is {row}")
                            if "Per" in row:
                                nutrition_per = row.split(' ')[-1].removesuffix(':')
                            elif "Energy" in row:
                                energy = row.split(' ')[-1]
                            elif "Fat" in row:
                                fat = row.split(' ')[-1]
                            elif "saturates" in row:
                                saturates = row.split(' ')[-1]
                            elif "Carbohydrate" in row:
                                carbs = row.split(' ')[-1]
                            elif "sugars" in row:
                                sugars = row.split(' ')[-1]
                            elif "Protein" in row:
                                protein = row.split(' ')[-1]
                            elif "Salt" in row:
                                salt = row.split(' ')[-1]
                    break
                except:
                    driver.refresh()
                    try_nutr = try_nutr + 1

            if try_nutr == MAX_TRY:
                print("ERROR: could not get nutrition")

            # insert to db
            if (real_weight == "ERROR") | (real_unit == "ERROR") | (item_price_in_pence == "ERROR"):
                print("Could not insert due to ERROR")
                driver.back()
                continue

            new_doc = {
                "ingredientTag": keyword,
                "ingredientCategory": category,
                "ingredientName": item_name_text,
                "storeName": "Aldi",
                "weight": real_weight,
                "unit": real_unit,
                "price": item_price_in_pence,
                "nutrition_per": nutrition_per,
                "energy": energy,
                "fat": fat,
                "saturates": saturates,
                "carbs": carbs,
                "sugars": sugars,
                "protein": protein,
                "salt": salt
            }

            # check if this ingredient with this tag with this store is already in db
            check_doc = {
                "ingredientTag": keyword,
                "ingredientName": item_name_text,
                "ingredientCategory": category,
                "storeName": "Aldi"
            }

            if collection.find_one(check_doc) is not None:
                print(f"{item_name_text} is already in db.")
                # if item already in db, check if data is unchanged
                if collection.find_one(new_doc) is not None:
                    # data is unchanged, no need to insert.
                    print("skip")
                    # navigate back to search results
                    driver.back()
                    continue
                    #try:
                        # navigate back to search results
                        #WebDriverWait(driver, 60).until(
                            #EC.element_to_be_clickable(
                                #driver.find_element(By.XPATH, "//a[@class='pull-left']"))).click()
                        #continue
                    #except:
                        #print("Could not navigate back to search results")
                        #break
                else:
                    # data has changed: update data
                    # update weight, unit, price
                    print("Update db.")
                    collection.update_one(check_doc, {"$set": {"weight": real_weight, "unit": real_unit, "price": item_price_in_pence}})
                    if (energy != "UNSPECIFIED") & (energy != "ERROR"):
                        # update nutritional information only if there was no error.
                        print("Updated nutritional values in db.")
                        collection.update_one(check_doc, {"$set": new_doc})

            else:
                # insert new item
                print("Inserted.")
                collection.insert_one(new_doc)

            # navigate back to search results
            driver.back()

            #try:
            #    WebDriverWait(driver, 120).until(
            #        EC.element_to_be_clickable(driver.find_element(By.XPATH, "//a[@class='pull-left']"))).click()
            #except:
            #    print("Could not navigate back to search results")
            #    break

        # navigate to the next page
        # ActionChains(driver).move_to_element(driver.find_element(By.XPATH, "//a[@title='Next']")).click().perform()
        # print("NEXT PAGE SKIPPED")


# Send a ping to confirm a successful connection
# try:
# client.admin.command('ping')
# print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
# print(e)

if __name__ == "__main__":
    main()
