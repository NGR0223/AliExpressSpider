from selenium import webdriver
from selenium.common import NoSuchFrameException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains, EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import time
import easyocr
import logging

ALIEXPRESS_URL = 'https://aliexpress.com'
ALIEXPRESS_UNAME = 'ngr0223@gmail.com'
ALIEXPRESS_PWD = 'mWs!Cr26i3.PirB'

logger = logging.getLogger('root')
logger.setLevel(level=logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class AliExpressSpider:
    def __init__(self, browser: str):
        self.m_spider = None
        if browser == 'Edge':
            self.browser_nit(browser)
            self.list_cates_info = []
            self.num_current_page = 1

            self.m_logger = logging.getLogger('AliExpressSpider')
            self.m_logger.info("Init")
        else:
            exit(-1)

    def browser_nit(self, browser: str):
        option = EdgeOptions()
        # 屏蔽“受自动化控制”
        option.add_experimental_option('excludeSwitches', ['enable-automation', 'load-extension'])

        # 屏蔽“保存密码”
        prefs = {"credentials_enable_service": False,
                 "profile.password_manager_enabled": False}
        option.add_experimental_option("prefs", prefs)

        # 关闭网站通知
        option.add_argument('--disable-notifications')
        self.m_spider = webdriver.Edge(options=option)

    def try_to_get_page(self, page_url):
        try:
            self.m_spider.get(page_url)
            self.m_spider.maximize_window()
            return True
        except:
            self.m_logger.error(f'Failed to get the page({page_url})')
            return False

    def scroll_to_end_of_page(self):
        px_each_time = 200
        for i in range(0, 20):
            self.m_spider.execute_script("window.scrollTo(0," + str(px_each_time) + ")")
            px_each_time += 200
            time.sleep(0.5)

    def login(self):
        # 登录账号
        self.m_spider.find_element(By.ID, 'fm-login-id').send_keys(ALIEXPRESS_UNAME)
        self.m_spider.find_element(By.ID, 'fm-login-password').send_keys(ALIEXPRESS_PWD)
        self.m_spider.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 滑动验证
        WebDriverWait(self.m_spider, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, 'baxia-dialog-content')))
        slide_ele = WebDriverWait(self.m_spider, 10).until(EC.visibility_of_element_located((By.ID, 'nc_1_n1z')))
        ActionChains(self.m_spider).click_and_hold(slide_ele).move_by_offset(316, 0).perform()

    def get_all_cates(self):
        if self.try_to_get_page(ALIEXPRESS_URL):
            while True:
                try:
                    self.m_spider.find_element(By.ID, 'fm-login-id')
                    self.login()
                except NoSuchElementException:
                    break

            # 关闭优惠通知
            # x = position-0 + length-400 - border-23
            # y = position-0 + border-23
            close_ele = WebDriverWait(self.m_spider, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "img[style='position: absolute; width: 36px; height:"
                                                                   " 36px; right: 5px; top: 5px; cursor: pointer;']")))
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
                self.list_cates_info.append(dict_tmp_cate_info)
            return True
        else:
            return False

    def get_store_url_of_page(self):
        self.scroll_to_end_of_page()
        list_cards_store_ele = self.m_spider.find_elements(By.CSS_SELECTOR, "a[role='store']")
        self.m_logger.info(f'The current page has {len(list_cards_store_ele)} in total')
        tmp_list_store_url = []
        for cards_store in list_cards_store_ele:
            tmp_list_store_url.append(cards_store.get_attribute('href'))
            self.m_logger.info(cards_store.get_attribute('href'))
        return tmp_list_store_url

    def start_to_spy(self):
        # 获取所有分类
        self.m_logger.info("Start to get all cates")
        if self.get_all_cates():
            self.m_logger.info("Successfully get all categories and their links")

            # 遍历所有分类
            for cate_info in self.list_cates_info:
                self.num_current_page = 1
                self.m_logger.info(f'Start to get store info of {cate_info["name"]}')

                # 打开分类的第一页
                if self.try_to_get_page(cate_info["link"]):
                    # 循环获取所有页的商店信息
                    while True:
                        # 获取当前页信息
                        self.m_logger.info(f'Start to get store info of Page{self.num_current_page}')
                        tmp_list_store_url = self.get_store_url_of_page()

                        for store_url in tmp_list_store_url:
                            tmp_spider = StoreInfoSpider(store_url)
                            tmp_spider.get_store_info_pic()
                            tmp_spider.pic_ocr()
                        # 向后翻页
                        try:
                            next_page_ele = self.m_spider.find_element(By.CSS_SELECTOR, "link[rel='next']")
                            self.try_to_get_page(next_page_ele.get_attribute('href'))

                            self.num_current_page += 1
                        except NoSuchElementException:
                            break
                else:
                    ...
        else:
            self.m_logger.info("Exit")

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
    testAliExpressSpider = AliExpressSpider('Edge')
    testAliExpressSpider.start_to_spy()
    testAliExpressSpider.destroy()
