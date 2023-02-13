from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains, EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from pybloom_live import ScalableBloomFilter
import os, csv, time, logging

CATES_CSV_FILE = 'cates.csv'  # 分类信息文件
INFO_CSV_FILE = 'info.csv'  # 商家信息文件
GOTTEN_STORE_BLOOM = 'GottenStore.blm'
ALIEXPRESS_URL = 'https://aliexpress.com'
ALIEXPRESS_UNAME = 'ngr0223@gmail.com'
ALIEXPRESS_PWD = 'mWs!Cr26i3.PirB'
PREFIX_LICENSE_LINK = 'https://sellerjoin.aliexpress.com/credential/showcredential.htm?storeNum='

logger = logging.getLogger('root')
logger.setLevel(level=logging.DEBUG)
formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def write_csv(list_info):
    with open(INFO_CSV_FILE, 'a+', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(list_info)


class AliExpressSpider:
    def __init__(self, browser: str):
        self.m_logger = logging.getLogger('AliExpressSpider')
        self.m_logger.info("Init")

        self.m_bf = None
        self.bloom_filter_init()

        self.m_spider = None
        self.list_cates_info = []
        self.num_current_page = 1
        if browser == 'Edge':
            self.browser_nit(browser)
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

    def bloom_filter_init(self):
        if os.path.exists(GOTTEN_STORE_BLOOM):
            self.m_bf = ScalableBloomFilter().fromfile(open(GOTTEN_STORE_BLOOM, 'rb'))
        else:
            self.m_bf = ScalableBloomFilter()

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

    def slide_verification_by_offset(self, offset):
        slide_ele = self.m_spider.find_element(By.ID, 'nc_1_n1z')
        ActionChains(self.m_spider).click_and_hold(slide_ele).move_by_offset(xoffset=offset, yoffset=0).perform()
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
                    self.m_spider.find_element(By.CSS_SELECTOR, "input[id^='fm-login']")
                    self.login()
                except NoSuchElementException:
                    break

            # 关闭优惠通知
            # x = position-0 + length-400 - border-23
            # y = position-0 + border-23
            # position: absolute; width: 36px; height: 36px; right: 5px; top: 5px; cursor: pointer;
            try:
                close_ele = WebDriverWait(self.m_spider, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR,
                                                                                                     "img[style='position: absolute; width: 36px; height: 36px; right: 5px; top: 5px; cursor: pointer;']")))
                ActionChains(self.m_spider).move_to_element(close_ele).click().perform()
            except NoSuchElementException:
                ...
        else:
            return False
        if os.path.isfile(CATES_CSV_FILE):
            with open(CATES_CSV_FILE, encoding='utf-8') as cates_csv_f:
                iter_csv_file = csv.reader(cates_csv_f)
                header = next(iter_csv_file)
                for row in iter_csv_file:
                    dict_tmp_cate_info = {'name': row[0], 'link': row[1]}
                    self.list_cates_info.append(dict_tmp_cate_info)
        if len(self.list_cates_info) != 0:
            return True
        else:
            # 找到所有一级菜单，将光标移至上方以加载二级菜单
            list_first_menu_ele = self.m_spider.find_elements(By.CSS_SELECTOR, "dl[data-role='first-menu']")
            for first_menu_ele in list_first_menu_ele:
                ActionChains(self.m_spider).move_to_element(first_menu_ele).perform()
                time.sleep(1)
            # 获取二级菜单名称和链接，并保存
            list_two_menu_ele = self.m_spider.find_elements(By.CSS_SELECTOR,
                                                            "dl[data-role='two-menu'] > dd > a")
            with open(CATES_CSV_FILE, 'a+', newline='') as cates_csv_f:
                csv_writer = csv.writer(cates_csv_f)
                for two_menu_ele in list_two_menu_ele:
                    dict_tmp_cate_info = {'name': two_menu_ele.get_attribute('innerText'),
                                          'link': two_menu_ele.get_attribute('href')}
                    self.list_cates_info.append(dict_tmp_cate_info)

                    # 写入到CSV保存，避免下次再次读取
                    csv_writer.writerow([dict_tmp_cate_info['name'], dict_tmp_cate_info['link'], 0])
            return True

    def get_store_url_of_page(self):
        self.scroll_to_end_of_page()
        list_cards_store_ele = self.m_spider.find_elements(By.CSS_SELECTOR, "a[role='store']")
        self.m_logger.info(f'The current page has {len(list_cards_store_ele)} link in total')
        tmp_list_store_url = []
        link_count = 1
        for cards_store in list_cards_store_ele:
            tmp_list_store_url.append(cards_store.get_attribute('href'))
            self.m_logger.info(f"Link {link_count} : {cards_store.get_attribute('href')}")
            link_count += 1
        return tmp_list_store_url

    def get_store_info_pic(self, store_num):
        license_page_url = PREFIX_LICENSE_LINK + store_num
        if self.try_to_get_page(license_page_url):
            retry = 0
            while True:
                load_flag = 0
                # 滑动验证
                try:
                    self.m_spider.find_element(By.ID, 'nc_1_n1z')
                    self.slide_verification_by_offset(258)
                except (NoSuchElementException, ElementNotInteractableException):
                    load_flag += 1
                # 点击错误提示刷新页面
                try:
                    refresh_ele = self.m_spider.find_element(By.ID, 'nc_1_refresh1')
                    ActionChains(self.m_spider).move_to_element(refresh_ele).click().perform()
                    time.sleep(0.5)
                except NoSuchElementException:
                    load_flag += 1
                if load_flag == 2:
                    break
                time.sleep(3)  # 等待页面刷新

                # 最多重试十次
                retry += 1
                if retry > 10:
                    self.m_logger.info(f'Failed to get picture of {store_num} after ten retries')
                    break
            # # 截图
            # self.m_spider.save_screenshot(f'StoreInfoPic/{store_num}.png')

            # 获取所需要的信息
            try:
                info_name_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "#container div[class='label']")
                info_content_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "#container div[class='content-en']")
                list_info = [store_num, '', '', '', '']
                for i, info_name_elem in enumerate(info_name_elems):
                    if info_name_elem.text == 'Company name：':
                        list_info[1] = info_content_elems[i].text
                        pass
                    elif info_name_elem.text == 'Address：':
                        list_info[2] = info_content_elems[i].text
                        pass
                    elif info_name_elem.text == 'Business Scope：':
                        list_info[3] = info_content_elems[i].text
                        pass
                    elif info_name_elem.text == 'Established：':
                        list_info[4] = info_content_elems[i].text
                        pass
                    else:
                        ...

                self.m_logger.info(str(list_info))
                write_csv(list_info)
            except NoSuchElementException:
                ...
        else:
            return False

    def start_to_spy(self):
        # 获取所有分类
        self.m_logger.info("Start to get all cates")
        if self.get_all_cates():
            self.m_logger.info("Successfully get all categories and their links")
            # 遍历所有分类
            for cate_info in self.list_cates_info:
                self.num_current_page = 1
                self.m_logger.info(f'Start to get store link of {cate_info["name"]}')

                # 打开分类的第一页
                if self.try_to_get_page(cate_info["link"]):
                    # 循环获取所有页的商店信息
                    while True:
                        # 获取当前页信息
                        self.m_logger.info(f'Start to get store link of Page {self.num_current_page}')
                        tmp_list_store_url = self.get_store_url_of_page()

                        for store_url in tmp_list_store_url:
                            start_index_store_num = store_url.rindex('/')
                            store_num = store_url[start_index_store_num + 1:]
                            self.m_logger.info(f'Start to get store info of {store_num}')
                            if not self.m_bf.add(store_num):
                                self.get_store_info_pic(store_num)
                                self.m_logger.info(f'Successfully get store info of {store_num}')
                            else:
                                self.m_logger.info(f'Already get store info of {store_num}')
                            time.sleep(1)

                            # 偶尔提示“通过验证以确保正常访问”
                            try:
                                self.m_spider.find_element(By.ID, 'nc_1_n1z')
                                self.slide_verification_by_offset(258)
                            except (NoSuchElementException, ElementNotInteractableException):
                                pass
                        self.m_bf.tofile(open(GOTTEN_STORE_BLOOM, 'wb'))

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


if __name__ == "__main__":
    testAliExpressSpider = AliExpressSpider('Edge')
    testAliExpressSpider.start_to_spy()
    testAliExpressSpider.destroy()
