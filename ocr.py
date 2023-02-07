import easyocr
import csv
import os
import re

INFO_CSV_FILE = 'info.csv'


def pic_ocr(store_id):
    reader = easyocr.Reader(['ch_sim', 'en'])
    result = reader.readtext(f'StoreInfoPic/{store_id}.png')

    # 完成寻找相关信息标记
    flag_complete = 0
    # 所需信息在ocr结果中索引
    index_company_start = 0
    index_company_end = 0
    index_address_start = 0
    index_address_end = 0
    index_time_start = 0
    index_time_end = 0
    for i, r in enumerate(result):
        if r[1][:-1] == 'Company name':
            index_company_start = i + 1
        elif r[1][:-1] == 'VAT numbe' or r[1][:-1] == 'VAT number':
            index_company_end = i
        elif r[1][:-1] == 'Address':
            index_address_start = i + 1
        elif r[1][:-1] == 'Legal Representative':
            index_address_end = i
        elif r[1][:-1] == 'Established':
            index_time_start = i + 1
        elif r[1][:-1] == 'Registration authority':
            index_time_end = i
        else:
            ...
    # 根据索引拼接所需要信息
    list_info = [store_id, '', '', '']  # company_name, address, time
    for index_company in range(index_company_start, index_company_end, 1):
        list_info[1] += re.sub('[\u4e00-\u9fa5]', '', result[index_company][1]) + ' '
    for index_address in range(index_address_start, index_address_end, 1):
        list_info[2] += re.sub('[\u4e00-\u9fa5]', '', result[index_address][1]) + ' '
    for index_time in range(index_time_start, index_time_end, 1):
        list_info[3] += re.sub('[\u4e00-\u9fa5]', '', result[index_time][1]) + ' '

    print(list_info)
    return list_info


def write_csv(list_info):
    with open(INFO_CSV_FILE, 'a+', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(list_info)


if __name__ == '__main__':
    for root, dirs, files in os.walk('StoreInfoPic/'):
        for file in files:
            tmp_store_id = str(file[:-4])
            tmp_list_info = pic_ocr(tmp_store_id)
            write_csv(tmp_list_info)
