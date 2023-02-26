import time
import pandas
import redis.exceptions
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from redisbloom.client import Client


class WishCrawler:
    def __init__(self):
        self.m_rb = None
        self.m_crawler = None

        self.redis_bloom_init()
        self.crawler_init()

    def redis_bloom_init(self):
        self.m_rb = Client(host='127.0.0.1', port=6379)
        try:
            self.m_rb.bfInfo('ProductBloom')
        except redis.exceptions.ResponseError:
            self.m_rb.bfCreate('ProductBloom', 0.0001, 16000000)

    def crawler_init(self):
        options = ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        # options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        # options.add_argument('-ignore-certificate-errors')
        # options.add_argument('-ignore -ssl-errors')
        service = Service(r"./chromedriver.exe")
        self.m_crawler = webdriver.Chrome(service=service, options=options)

    # 需要提前打开分类页面
    def crawl(self):
        start_data_index = 0
        while True:
            data_index_elems = self.m_crawler.find_elements(By.CSS_SELECTOR, 'div[data-index]')
            for data_index_elem in data_index_elems:
                cur_data_index = int(data_index_elem.get_attribute('data-index'))
                if cur_data_index >= start_data_index:
                    product_elems = self.m_crawler.find_elements(
                        By.CSS_SELECTOR, f'div[data-index="{cur_data_index}"] a[class*="FeedTile__Wrapper-sc"]')
                    for product_elem in product_elems:
                        product_id = product_elem.get_attribute('data-id')
                        print(product_id)
                else:
                    pass

            start_data_index = int(data_index_elems[-1].get_attribute('data-index')) + 1
            # 滚动到底部
            self.m_crawler.execute_script('window.scrollTo(0, document.documentElement.scrollHeight)')
            self.m_crawler.wait_util()

def save_excel(data):
    data_frame = pandas.DataFrame(data=data, columns=['店铺名', '时间', '地址'])
    data_frame.to_excel('merch_info1.xls', index=False)


if __name__ == '__main__':
    menu_list = ['Trending', 'Fashion', 'Baby Gear', 'Pet Accessories', 'Gadgets', 'Tools', 'Health and Beauty',
                 'Drinks and Smokes', 'Home and Garden', 'Home Improvement', 'Art and Craft Supplies',
                 'Toys and Hobbies', 'Sports and Outdoor Gear', 'Automotive Accessories']

    wish = WishCrawler()
    wish.crawl()
