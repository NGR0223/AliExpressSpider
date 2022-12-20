from selenium import webdriver
from selenium.common import UnexpectedAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import time
import easyocr

ALIEXPRESS_URL = 'https://aliexpress.com'


class AliExpressSpider:
    def __init__(self, browser: str):
        if browser == 'Edge':
            self.m_spider = webdriver.Edge()
            self.list_cates_info = []
        else:
            exit(-1)

    def try_to_get_page(self, page_url):
        try:
            self.m_spider.get(page_url)
            self.m_spider.maximize_window()
            return True
        except:
            print(f'Failed to get the page({page_url})')
            return False

    def scroll_to_end_of_page(self):
        px_each_time = 200
        for i in range(0, 20):
            self.m_spider.execute_script("window.scrollTo(0," + str(px_each_time) + ")")
            px_each_time += 200
            time.sleep(0.1)

    def get_all_cates(self):
        if self.try_to_get_page(ALIEXPRESS_URL):
            # 关闭订阅通知
            # x = position-80 + length-476 - border-14
            # y = position-10 + border-14
            ActionChains(self.m_spider).move_by_offset(542, 24).click().perform()

            # 关闭优惠通知#
            # x = position-0 + length-400 - border-23
            # y = position-0 + border-23
            close_ele = self.m_spider.find_element(By.CSS_SELECTOR,
                                                   "img[style='position: absolute; width: 36px; height: 36px; right: 5px; top: 5px; cursor: pointer;']")
            ActionChains(self.m_spider).move_to_element(close_ele).click().perform()

            # 找到所有一级菜单，将光标移至上方以加载二级菜单
            list_first_menu_ele = self.m_spider.find_elements(By.CSS_SELECTOR, "dl[data-role='first-menu']")
            for first_menu_ele in list_first_menu_ele:
                ActionChains(self.m_spider).move_to_element(first_menu_ele).perform()
                time.sleep(1)
            # 获取二级菜单名称和链接，并保存
            list_two_menu_ele = self.m_spider.find_elements(By.CSS_SELECTOR, "dl[data-role='two-menu'] > dd > a")
            for two_menu_ele in list_two_menu_ele:
                dict_tmp_cate_info = {'name': two_menu_ele.get_attribute('innerText'),
                                      'link': two_menu_ele.get_attribute('href')}
                # print(two_menu_ele.get_attribute('innerText'))
                # print(two_menu_ele.get_attribute('href'))
            print("Successfully get all categories and their links")
            return True
        else:
            return False

    def get_store_url_of_page(self, page_url):
        if self.try_to_get_page(page_url):
            self.scroll_to_end_of_page()
            list_cards_store_ele = self.m_spider.find_elements(By.CSS_SELECTOR, "a[role='store']")
            print(len(list_cards_store_ele))
            for cards_store in list_cards_store_ele:
                print(cards_store.get_attribute('href'))
        else:
            return False

    def destroy(self):
        self.m_spider.quit()


class StoreInfoSpider:
    m_store_name = ''

    def __init__(self, store_url: str):
        self.m_store_url = store_url

    def get_store_info_pic(self):
        # 打开商店主页
        driver = webdriver.Edge()
        driver.get(self.m_store_url)
        driver.maximize_window()

        # 找到商店名称元素，并将光标移动到其上方
        # xpath = //*[@id="hd"]/div/div/div[1]/div[2]/div[1]/div/div/div[1]/div[1]/a
        store_name_ele = driver.find_element(By.XPATH,
                                             '//*[@id="hd"]/div/div/div[1]/div[2]/div[1]/div/div/div[1]/div[1]/a')
        self.m_store_name = store_name_ele.accessible_name
        ActionChains(driver).move_to_element(store_name_ele).perform()

        # 找到Business License元素并点击
        # xpath = /html/body/div[11]/div/div/div[1]/div[1]/a
        try:
            licence_link_ele = driver.find_element(By.XPATH, '/html/body/div[10]/div/div/div[1]/div[1]/a')
        except:
            print("Cannot not find license link")
            return
        licence_link_ele.click()
        time.sleep(5)

        # 将句柄切换到新开启的页面
        pages = driver.window_handles
        driver.switch_to.window(pages[1])

        # 找到滑块元素，并按住向右滑动258个像素
        slide_ele = driver.find_element(By.ID, 'nc_1_n1z')
        ActionChains(driver).click_and_hold(slide_ele).perform()
        ActionChains(driver).move_by_offset(xoffset=258, yoffset=0).perform()
        time.sleep(0.1)  # 模拟鼠标停留
        ActionChains(driver).release(slide_ele).perform()
        time.sleep(5)  # 等待页面刷新

        # 截图
        driver.save_screenshot(f'StoreInfoPic/{self.m_store_name}.png')

        # 退出
        driver.quit()

    def pic_ocr(self):
        reader = easyocr.Reader(['ch_sim', 'en'])
        result = reader.readtext(f'StoreInfoPic/{self.m_store_name}.png')
        print(result)


if __name__ == "__main__":
    # spider = StoreInfoSpider("https://www.aliexpress.com/store/1101287070")
    # spider.get_store_info_pic()
    # spider.pic_ocr()
    testAliExpressSpider = AliExpressSpider('Edge')
    testAliExpressSpider.get_all_cates()
    # start_page = 'https://www.aliexpress.com/category/100003071/t-shirts.html'
    # testAliExpressSpider.get_num_pages(start_page)
    # page_url = 'https://www.aliexpress.com/category/100003084/hoodies-&-sweatshirts.html?category_redirect=1&dida=y'
    # testAliExpressSpider.get_store_url_of_page(page_url)
    testAliExpressSpider.destroy()
