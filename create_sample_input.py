"""
サンプル入力ファイル（facilities.xlsx）を作成するスクリプト

動作確認用に使用してください。
"""

import pandas as pd

# サンプルデータ
sample_data = {
    '施設名': [
        'ホテルサンプル',
        '旅館テスト',
        'リゾートホテルABC',
        'ビジネスホテルXYZ'
    ],
    '地域': [
        '東京都',
        '京都府',
        '沖縄県',
        '大阪府'
    ],
    '電話番号': [
        '03-1234-5678',
        '075-1234-5678',
        '098-1234-5678',
        '06-1234-5678'
    ]
}

df = pd.DataFrame(sample_data)
df.to_excel('facilities.xlsx', index=False)
print('✅ サンプル入力ファイル facilities.xlsx を作成しました。')

