import subprocess

cmd_edge = '"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" ' \
           '--remote-debugging-port=9222 ' \
           '--user-data-dir="D:\\PycharmProjects\\AliExpressSpider\\EdgeProfile"'

cmd_chrome = '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ' \
             '--remote-debugging-port=9222 ' \
             '--disable-notifications ' \
             '--user-data-dir="D:\\PycharmProjects\\AliExpressSpider\\ChromeProfile"'

proc = subprocess.Popen(cmd_chrome)
# proc.kill()
pass
