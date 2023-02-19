import os
import csv
import time
import logging
import subprocess
from random import randint
from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException, InvalidArgumentException, \
    WebDriverException, NoSuchFrameException
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains, EdgeOptions
from selenium.webdriver.chrome.webdriver import Options
from pybloom_live import ScalableBloomFilter

CATES_CSV_FILE = 'cates.csv'  # 分类信息文件
INFO_CSV_FILE = 'info.csv'  # 商家信息文件
CONFIG_JSON_FILE = 'config.json'  # 爬虫配置记录文件
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


def write_csv(infos: list):
    with open(INFO_CSV_FILE, 'a+', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(infos)


def get_track(distance):
    """
    拿到移动轨迹，模仿人的滑动行为，先匀加速后匀减速
    匀变速运动基本公式：
    ①v=v0+at
    ②s=v0t+(1/2)at²
    ③v²-v0²=2as
    :param distance: 需要移动的距离
    :return: 存放每0.2秒移动的距离
    """
    # 初速度
    v = 0
    # 单位时间为0.2s来统计轨迹，轨迹即0.2内的位移
    t = 0.1
    # 位移/轨迹列表，列表内的一个元素代表0.2s的位移
    tracks = []
    # 当前的位移
    current = 0
    # 到达mid值开始减速
    mid = distance * 7 / 8
    distance += 10  # 先滑过一点，最后再反着滑动回来
    # a = random.randint(1,3)
    while current < distance:
        if current < mid:
            # 加速度越小，单位时间的位移越小,模拟的轨迹就越多越详细
            a = randint(13, 16)  # 加速运动
        else:
            a = -randint(13, 16)  # 减速运动
        # 初速度
        v0 = v
        # 0.2秒时间内的位移
        s = v0 * t + 0.5 * a * (t ** 2)
        # 当前的位置
        current += s
        # 添加到轨迹列表
        tracks.append(round(s))
        # 速度已经达到v,该速度作为下次的初速度
        v = v0 + a * t
    # 反着滑动到大概准确位置
    for i in range(2):
        tracks.append(-randint(2, 3))
    for i in range(2):
        tracks.append(-randint(1, 3))

    return tracks


class AliExpressSpider:
    def __init__(self, browser_type, start_index_cate):
        self.m_cate_infos = []
        self.m_links_current_page = []
        self.m_bf = None
        self.m_spider = None
        self.m_browser_type = browser_type
        self.m_start_index_cate = start_index_cate
        self.m_num_current_page = 0

        self.bloom_filter_init()
        self.browser_init()

        self.m_logger = logging.getLogger('AliExpressSpider')
        self.m_logger.info("Init")

    def browser_init(self):
        if self.m_browser_type:
            option = EdgeOptions()
            # 连接到手动启动的浏览器
            option.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            self.m_spider = webdriver.Edge(options=option)
        else:
            option = Options()
            # 连接到手动启动的浏览器
            option.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            self.m_spider = webdriver.Chrome(options=option)

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
        except (InvalidArgumentException, WebDriverException):
            self.m_logger.error(f'Failed to get the page({page_url})')
            return False

    def scroll_to_end_of_page(self):
        px_each_time = 200
        for i in range(0, 20):
            self.m_spider.execute_script("window.scrollTo(0," + str(px_each_time) + ")")
            px_each_time += 200
            time.sleep(0.2)

    def slide_verification_by_offset(self, offset):
        slide_elem = self.m_spider.find_element(By.ID, 'nc_1_n1z')
        tracks = get_track(offset)
        ActionChains(self.m_spider).click_and_hold(slide_elem).perform()
        time.sleep(0.2)
        for track in tracks:
            ActionChains(self.m_spider).move_by_offset(xoffset=track, yoffset=0).perform()
            time.sleep(0.001)

    def login(self):
        self.m_logger.info(f'Login')
        # 登录账号
        self.m_spider.find_element(By.ID, 'fm-login-id').send_keys(ALIEXPRESS_UNAME)
        self.m_spider.find_element(By.ID, 'fm-login-password').send_keys(ALIEXPRESS_PWD)
        self.m_spider.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(1)

        # 滑动验证
        try:
            iframe_elem = self.m_spider.find_element(By.ID, 'baxia-dialog-content')
            self.m_spider.switch_to.frame(iframe_elem)
            self.slide_verification_by_offset(316)
        except (NoSuchElementException, NoSuchFrameException):
            pass

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
                close_elem = self.m_spider.find_element(By.CSS_SELECTOR,
                                                        "img[style='position: absolute; width: 36px; height: 36px; "
                                                        "right: 5px; top: 5px; cursor: pointer;']")
                ActionChains(self.m_spider).move_to_element(close_elem).click().perform()
            except NoSuchElementException:
                pass
        else:
            return False
        if os.path.isfile(CATES_CSV_FILE):
            with open(CATES_CSV_FILE, encoding='utf-8') as cates_csv_f:
                iter_csv_file = csv.reader(cates_csv_f)
                next(iter_csv_file)  # 去除表头
                for row in iter_csv_file:
                    dict_tmp_cate_info = {'name': row[0], 'link': row[1]}
                    self.m_cate_infos.append(dict_tmp_cate_info)
        if len(self.m_cate_infos) != 0:
            return True
        else:
            # 找到所有一级菜单，将光标移至上方以加载二级菜单
            first_menu_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "dl[data-role='first-menu']")
            for first_menu_elem in first_menu_elems:
                ActionChains(self.m_spider).move_to_element(first_menu_elem).perform()
                time.sleep(1)
            # 获取二级菜单名称和链接，并保存
            two_menu_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "dl[data-role='two-menu'] > dd > a")
            with open(CATES_CSV_FILE, 'a+', newline='') as cates_csv_f:
                csv_writer = csv.writer(cates_csv_f)
                for two_menu_elem in two_menu_elems:
                    dict_tmp_cate_info = {'name': two_menu_elem.get_attribute('innerText'),
                                          'link': two_menu_elem.get_attribute('href')}
                    self.m_cate_infos.append(dict_tmp_cate_info)

                    # 写入到CSV保存，避免下次再次读取
                    csv_writer.writerow([dict_tmp_cate_info['name'], dict_tmp_cate_info['link'], 0])
            return True

    def get_store_url_of_page(self):
        self.scroll_to_end_of_page()
        cards_store_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "a[role='store']")
        self.m_logger.info(f'The current page has {len(cards_store_elems)} link in total')
        tmp_store_links = []
        link_count = 1
        for cards_store_elem in cards_store_elems:
            tmp_store_links.append(cards_store_elem.get_attribute('href'))
            self.m_logger.info(f"Link {link_count} : {cards_store_elem.get_attribute('href')}")
            link_count += 1
        return tmp_store_links

    def get_store_info(self, store_num):
        license_page_url = PREFIX_LICENSE_LINK + store_num
        if self.try_to_get_page(license_page_url):
            retry = 0
            while True:
                # 直到加载出信息页面跳出循环
                try:
                    self.m_spider.find_element(By.CSS_SELECTOR, "#container div[class='label']")
                    break
                except NoSuchElementException:
                    ...

                # 滑动验证
                try:
                    self.m_spider.find_element(By.ID, 'nc_1_n1z')
                    self.slide_verification_by_offset(258)
                except (NoSuchElementException, ElementNotInteractableException):
                    ...

                # 点击错误提示刷新页面
                try:
                    refresh_elem = self.m_spider.find_element(By.CSS_SELECTOR, "[id*='nc_1_refresh1']")
                    ActionChains(self.m_spider).move_to_element(refresh_elem).click().perform()
                    time.sleep(0.5)
                except NoSuchElementException:
                    ...
                time.sleep(1)  # 等待页面刷新

                # 最多重试十次
                retry += 1
                if retry > 10:
                    self.m_logger.info(f'Failed to get info of {store_num} after ten retries')
                    return -2
            # 获取所需要的信息
            try:
                info_name_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "#container div[class='label']")
                info_content_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "#container div[class='content-en']")
                infos = [store_num, '', '', '', '']
                match_count = 0
                for i, info_name_elem in enumerate(info_name_elems):
                    if info_name_elem.text == 'Company name：':
                        infos[1] = info_content_elems[i].text
                        match_count += 1
                        pass
                    elif info_name_elem.text == 'Address：':
                        infos[2] = info_content_elems[i].text
                        match_count += 1
                        pass
                    elif info_name_elem.text == 'Business Scope：':
                        infos[3] = info_content_elems[i].text
                        match_count += 1
                        pass
                    elif info_name_elem.text == 'Established：':
                        infos[4] = info_content_elems[i].text
                        match_count += 1
                        pass
                    else:
                        pass
                if match_count >= 2:
                    write_csv(infos)
                    return 0
                else:
                    return -4
            except NoSuchElementException:
                return -3
        else:
            return -1

    def start_to_spy(self):
        link_current_page = ''
        # 获取所有分类
        self.m_logger.info("Start to get all cates")
        if self.get_all_cates():
            self.m_logger.info("Successfully get all categories and their links")
            # 调整类别链接列表
            tmp_cate_infos = self.m_cate_infos[self.m_start_index_cate:] + self.m_cate_infos[:self.m_start_index_cate]
            # 遍历所有分类
            for cate_info in tmp_cate_infos:
                self.m_num_current_page = 1
                self.m_logger.info(f'Start to get store link of {cate_info["name"]}')

                # 打开分类的第一页
                if self.try_to_get_page(cate_info["link"]):
                    # 此时仍然可能需要登录
                    try:
                        self.m_spider.find_element(By.CSS_SELECTOR, "input[id^='fm-login']")
                        self.login()
                    except NoSuchElementException:
                        pass

                    # 循环获取所有页的商店信息
                    while True:
                        # 获取当前页信息
                        self.m_logger.info(f'Start to get store link of Page {self.m_num_current_page}')
                        # 获取当前页面链接
                        link_current_page = self.m_spider.current_url
                        self.m_links_current_page = self.get_store_url_of_page()

                        tmp_links_current_page = self.m_links_current_page[:]
                        for store_link in tmp_links_current_page:
                            start_index_store_num = store_link.rindex('/')
                            store_num = store_link[start_index_store_num + 1:]
                            self.m_logger.info(f'Start to get store info of {store_num}')
                            if store_num in self.m_bf:
                                self.m_logger.info(f'Already get store info of {store_num}')
                            else:
                                ret = self.get_store_info(store_num)
                                if ret == 0:
                                    self.m_logger.info(f'Successfully get store info of {store_num}')
                                    self.m_bf.add(store_num)
                                    self.m_links_current_page.remove(store_link)
                                elif ret == -1:
                                    self.m_logger.info(f'Failed to get info of {store_num} due to Page loading failure')
                                elif ret == -2:
                                    self.m_logger.info(f'Failed to get info of {store_num} due to Banned')
                                    return self.m_start_index_cate
                                elif ret == -3:
                                    self.m_logger.info(
                                        f'Failed to get info of {store_num} due to Web elements loading failure')
                                elif ret == -4:
                                    self.m_logger.info(
                                        f'Failed to get info of {store_num} due to Web elements loaded not enough')
                                else:
                                    self.m_logger.info(f'Failed to get info of {store_num} due to Unknown error')
                                time.sleep(randint(1, 3))

                            # 偶尔提示“通过验证以确保正常访问”
                            try:
                                self.m_spider.find_element(By.ID, 'nc_1_n1z')
                                self.slide_verification_by_offset(258)
                            except (NoSuchElementException, ElementNotInteractableException):
                                pass
                        self.m_bf.tofile(open(GOTTEN_STORE_BLOOM, 'wb'))

                        # 向后翻页
                        if self.try_to_get_page(link_current_page):
                            self.scroll_to_end_of_page()
                        try:
                            next_page_elem = self.m_spider.find_element(By.CSS_SELECTOR, "li[class$='next-next']")
                            ActionChains(self.m_spider).click(next_page_elem).perform()

                            self.m_num_current_page += 1
                        except NoSuchElementException:
                            break
                        # 页面存在，但页面内无数据
                        try:
                            self.m_spider.find_element(By.CSS_SELECTOR, "div[class^='list--gallery']")
                        except NoSuchElementException:
                            break
                    self.m_start_index_cate += 1
                else:
                    pass
                self.m_start_index_cate += 1
        else:
            self.m_logger.info("Exit")

    def destroy(self):
        self.m_spider.quit()


if __name__ == "__main__":
    cmd_edge = f'"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" ' \
               f'--remote-debugging-port=9222 ' \
               f'--disable-notification ' \
               f'--user-data-dir="{os.getcwd()}\\EdgeProfile"'

    cmd_chrome = f'"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ' \
                 f'--remote-debugging-port=9222 ' \
                 f'--disable-notifications ' \
                 f'--user-data-dir="{os.getcwd()}\\ChromeProfile"'
    browserType = False
    startIndexCate = 12
    while True:
        if browserType:
            proc = subprocess.Popen(cmd_edge)
        else:
            proc = subprocess.Popen(cmd_chrome)
        testAliExpressSpider = AliExpressSpider(browserType, startIndexCate)
        startIndexCate = testAliExpressSpider.start_to_spy()
        testAliExpressSpider.destroy()

        browserType = not browserType
        proc.kill()
