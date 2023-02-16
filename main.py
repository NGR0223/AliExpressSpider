import os
import csv
import time
import logging
from random import randint
import subprocess
from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException, InvalidArgumentException, \
    WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains, EdgeOptions
from selenium.webdriver.chrome.webdriver import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from pybloom_live import ScalableBloomFilter

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
    def __init__(self, browser):
        self.cate_infos = []
        self.links_current_page = []
        self.num_current_page = 1

        self.m_logger = logging.getLogger('AliExpressSpider')
        self.m_logger.info("Init")

        self.m_bf = None
        self.bloom_filter_init()

        self.m_spider = None
        self.browser_init(browser)

    def browser_init(self, browser):
        if browser:
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
            time.sleep(0.5)

    def slide_verification_by_offset(self, offset):
        slide_ele = self.m_spider.find_element(By.ID, 'nc_1_n1z')
        tracks = get_track(offset)
        ActionChains(self.m_spider).click_and_hold(slide_ele).perform()
        time.sleep(0.5)
        for track in tracks:
            ActionChains(self.m_spider).move_by_offset(xoffset=track, yoffset=0).perform()
            time.sleep(0.001)

    def login(self):
        # 登录账号
        self.m_spider.find_element(By.ID, 'fm-login-id').send_keys(ALIEXPRESS_UNAME)
        self.m_spider.find_element(By.ID, 'fm-login-password').send_keys(ALIEXPRESS_PWD)
        self.m_spider.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 滑动验证
        WebDriverWait(self.m_spider, 10).until(
            ec.frame_to_be_available_and_switch_to_it((By.ID, 'baxia-dialog-content')))
        try:
            WebDriverWait(self.m_spider, 10).until(ec.visibility_of_element_located((By.ID, 'nc_1_n1z')))
            self.slide_verification_by_offset(316)
        except NoSuchElementException:
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
                close_ele = self.m_spider.find_element(By.CSS_SELECTOR,
                                                       "img[style='position: absolute; width: 36px; height: 36px; "
                                                       "right: 5px; top: 5px; cursor: pointer;']")
                ActionChains(self.m_spider).move_to_element(close_ele).click().perform()
            except NoSuchElementException:
                ...
        else:
            return False
        if os.path.isfile(CATES_CSV_FILE):
            with open(CATES_CSV_FILE, encoding='utf-8') as cates_csv_f:
                iter_csv_file = csv.reader(cates_csv_f)
                next(iter_csv_file)  # 去除表头
                for row in iter_csv_file:
                    dict_tmp_cate_info = {'name': row[0], 'link': row[1]}
                    self.cate_infos.append(dict_tmp_cate_info)
        if len(self.cate_infos) != 0:
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
                    self.cate_infos.append(dict_tmp_cate_info)

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

    def get_store_info(self, store_num):
        license_page_url = PREFIX_LICENSE_LINK + store_num
        if self.try_to_get_page(license_page_url):
            retry = 0
            while True:
                ban_flag = False
                load_count = 0
                # 滑动验证
                try:
                    self.m_spider.find_element(By.ID, 'nc_1_n1z')
                    self.slide_verification_by_offset(258)
                except (NoSuchElementException, ElementNotInteractableException):
                    load_count += 1
                # 点击错误提示刷新页面
                try:
                    refresh_ele = self.m_spider.find_element(By.ID, 'nc_1_refresh1')
                    ActionChains(self.m_spider).move_to_element(refresh_ele).click().perform()
                    time.sleep(0.5)
                except NoSuchElementException:
                    load_count += 1
                if load_count == 2:
                    break
                time.sleep(3)  # 等待页面刷新

                # 最多重试十次
                retry += 1
                if retry > 10:
                    self.m_logger.info(f'Failed to get info of {store_num} after ten retries')
                    ban_flag = True
                    break
            if ban_flag:
                return -2
            # 获取所需要的信息
            try:
                info_name_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "#container div[class='label']")
                info_content_elems = self.m_spider.find_elements(By.CSS_SELECTOR, "#container div[class='content-en']")
                list_info = [store_num, '', '', '', '']
                match_count = 0
                for i, info_name_elem in enumerate(info_name_elems):
                    if info_name_elem.text == 'Company name：':
                        list_info[1] = info_content_elems[i].text
                        match_count += 1
                        pass
                    elif info_name_elem.text == 'Address：':
                        list_info[2] = info_content_elems[i].text
                        match_count += 1
                        pass
                    elif info_name_elem.text == 'Business Scope：':
                        list_info[3] = info_content_elems[i].text
                        match_count += 1
                        pass
                    elif info_name_elem.text == 'Established：':
                        list_info[4] = info_content_elems[i].text
                        match_count += 1
                        pass
                    else:
                        ...
                if match_count >= 2:
                    # self.m_logger.info(str(list_info))
                    write_csv(list_info)
                    return 0
                else:
                    return -4
            except NoSuchElementException:
                return -3
        else:
            return -1

    def start_to_spy(self):
        flag_restart = False
        # 获取所有分类
        self.m_logger.info("Start to get all cates")
        if self.get_all_cates():
            self.m_logger.info("Successfully get all categories and their links")
            # 遍历所有分类
            for cate_info in self.cate_infos:
                self.num_current_page = 1
                self.m_logger.info(f'Start to get store link of {cate_info["name"]}')

                # 打开分类的第一页
                if self.try_to_get_page(cate_info["link"]):
                    # 循环获取所有页的商店信息
                    while True:
                        # 获取当前页信息
                        self.m_logger.info(f'Start to get store link of Page {self.num_current_page}')
                        self.links_current_page = self.get_store_url_of_page()

                        tmp_links_current_page = self.links_current_page[:]
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
                                    self.links_current_page.remove(store_link)
                                elif ret == -1:
                                    self.m_logger.info(f'Failed to get info of {store_num} due to Page loading failure')
                                elif ret == -2:
                                    self.m_logger.info(f'Failed to get info of {store_num} due to Banned')
                                    flag_restart = True
                                    break
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

                        if flag_restart:
                            break

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
    cmd_edge = '"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" ' \
               '--remote-debugging-port=9222 ' \
               '--disable-notification ' \
               '--user-data-dir="D:\\PycharmProjects\\AliExpressSpider\\EdgeProfile"'

    cmd_chrome = '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ' \
                 '--remote-debugging-port=9222 ' \
                 '--disable-notifications ' \
                 '--user-data-dir="D:\\PycharmProjects\\AliExpressSpider\\ChromeProfile"'
    browser_type = True
    while True:
        if browser_type:
            proc = subprocess.Popen(cmd_edge)
        else:
            proc = subprocess.Popen(cmd_chrome)
        testAliExpressSpider = AliExpressSpider(browser_type)
        testAliExpressSpider.start_to_spy()
        testAliExpressSpider.destroy()

        browser_type = not browser_type
        proc.kill()
