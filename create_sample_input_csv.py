"""
サンプル入力CSVファイル（input.csv）を作成するスクリプト

動作確認用に使用してください。
"""

import csv

# サンプルデータ
sample_data = [
    {
        'facility_name': '民宿 やしろ',
        'phone_number': '090-1234-5678',
        'website_url': ''
    },
    {
        'facility_name': 'ペンション シーガル',
        'phone_number': '080-9876-5432',
        'website_url': 'https://example.com'
    },
    {
        'facility_name': 'リゾートホテル ABC',
        'phone_number': '03-1234-5678',
        'website_url': ''
    },
]

# CSVファイルに書き込み
with open('input.csv', 'w', encoding='utf-8-sig', newline='') as f:
    fieldnames = ['facility_name', 'phone_number', 'website_url']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    
    writer.writeheader()
    writer.writerows(sample_data)

print('✅ サンプル入力ファイル input.csv を作成しました。')

