from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import time


class StoreInfoSpider:
    m_store_name = ''

    def __init__(self, store_url: str):
        self.m_store_url = store_url

    def spy(self):
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
        time.sleep(0.1)
        ActionChains(driver).release(slide_ele).perform()
        time.sleep(1)

        # 截图
        driver.save_screenshot('tmp.png')

        # 退出
        driver.quit()


if __name__ == "__main__":
    spider = StoreInfoSpider("https://www.aliexpress.com/store/1101380133")
    spider.spy()
