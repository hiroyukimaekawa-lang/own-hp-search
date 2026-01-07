'use client';

import { useState } from 'react';

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('ファイルを選択してください');
      return;
    }

    if (!apiKey) {
      setError('APIキーを入力してください');
      return;
    }

    setProcessing(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('apiKey', apiKey);

      const response = await fetch('/api/process', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '処理に失敗しました');
      }

      setResult(data.csv);
      setProgress({ current: data.count, total: data.count });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;

    const blob = new Blob([result], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', '結果.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow-md rounded-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            宿泊施設公式サイト検索ツール
          </h1>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-2">
                Brave Search APIキー
              </label>
              <input
                type="password"
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="APIキーを入力してください"
                disabled={processing}
              />
            </div>

            <div>
              <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-2">
                CSVファイルをアップロード
              </label>
              <input
                type="file"
                id="file"
                accept=".csv"
                onChange={handleFileChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                disabled={processing}
              />
              <div className="mt-2 p-4 bg-gray-50 rounded-md">
                <p className="text-sm font-medium text-gray-700 mb-2">📋 CSVファイル形式</p>
                <p className="text-sm text-gray-600 mb-2">必須カラム: <span className="font-semibold">屋号</span></p>
                <div className="text-xs text-gray-600 space-y-1">
                  <p><strong>例:</strong></p>
                  <div className="bg-white p-2 rounded border border-gray-200 font-mono text-xs">
                    <div className="grid grid-cols-3 gap-2 mb-1">
                      <div className="font-semibold">A列: 屋号</div>
                      <div className="font-semibold">B列: 電話番号</div>
                      <div className="font-semibold">C列: website_url</div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-gray-600">
                      <div>民宿 やしろ</div>
                      <div>090-1234-5678</div>
                      <div></div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-gray-600">
                      <div>ペンション シーガル</div>
                      <div>080-9876-5432</div>
                      <div>https://example.com</div>
                    </div>
                  </div>
                  <p className="mt-2 text-gray-500">※ A列（1列目）に「屋号」カラムが必要です</p>
                  <p className="text-gray-500">※ カラム名は「屋号」または「屋号 」でも認識されます</p>
                </div>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            {processing && (
              <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded">
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700 mr-2"></div>
                  処理中... しばらくお待ちください
                </div>
              </div>
            )}

            {progress.total > 0 && !processing && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                処理完了: {progress.current}件
              </div>
            )}

            <button
              type="submit"
              disabled={processing || !file || !apiKey}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {processing ? '処理中...' : '検索を開始'}
            </button>
          </form>

          {result && (
            <div className="mt-8">
              <button
                onClick={handleDownload}
                className="w-full bg-green-600 text-white py-3 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
              >
                結果をダウンロード
              </button>
            </div>
          )}

          <div className="mt-8 pt-8 border-t border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">使い方</h2>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600 mb-6">
              <li>Brave Search APIキーを入力してください</li>
              <li>「屋号」カラムを含むCSVファイルをアップロードしてください</li>
              <li>「検索を開始」ボタンをクリックしてください</li>
              <li>処理が完了したら「結果をダウンロード」ボタンでCSVをダウンロードできます</li>
            </ol>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-md font-semibold text-blue-900 mb-3">📄 入力CSVファイル形式</h3>
              <div className="text-sm text-blue-800 space-y-2">
                <p><strong>必須カラム:</strong></p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>A列（1列目）: 屋号</strong> - 宿泊施設の名前（必須）</li>
                </ul>
                <p className="mt-3"><strong>CSVファイル例:</strong></p>
                <div className="bg-white p-3 rounded border border-blue-200 font-mono text-xs overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-2 py-1 text-left">A列: 屋号</th>
                        <th className="border border-gray-300 px-2 py-1 text-left">B列: 電話番号</th>
                        <th className="border border-gray-300 px-2 py-1 text-left">C列: website_url</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border border-gray-300 px-2 py-1">民宿 やしろ</td>
                        <td className="border border-gray-300 px-2 py-1">090-1234-5678</td>
                        <td className="border border-gray-300 px-2 py-1"></td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-2 py-1">ペンション シーガル</td>
                        <td className="border border-gray-300 px-2 py-1">080-9876-5432</td>
                        <td className="border border-gray-300 px-2 py-1">https://example.com</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-blue-700">
                  ※ A列（1列目）に「屋号」カラムが必要です<br/>
                  ※ カラム名は「屋号」または「屋号 」（末尾にスペース）でも認識されます<br/>
                  ※ 他のカラム（電話番号、website_urlなど）は任意です
                </p>
              </div>
            </div>

            <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="text-md font-semibold text-green-900 mb-3">📥 出力CSVファイル形式</h3>
              <div className="text-sm text-green-800 space-y-2">
                <p><strong>出力カラム:</strong></p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>A列: 屋号</strong> - 施設名</li>
                  <li><strong>B列: 自社HP</strong> - 見つかった自社の公式サイトURL（見つからない場合は空欄）</li>
                  <li><strong>C列: 他OTAなどのサイト</strong> - OTAサイトなどのURL（見つからない場合は空欄、複数ある場合はセミコロン区切り）</li>
                </ul>
                <p className="mt-3"><strong>出力CSVファイル例:</strong></p>
                <div className="bg-white p-3 rounded border border-green-200 font-mono text-xs overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-2 py-1 text-left">A列: 屋号</th>
                        <th className="border border-gray-300 px-2 py-1 text-left">B列: 自社HP</th>
                        <th className="border border-gray-300 px-2 py-1 text-left">C列: 他OTAなどのサイト</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border border-gray-300 px-2 py-1">民宿 やしろ</td>
                        <td className="border border-gray-300 px-2 py-1">https://example.com</td>
                        <td className="border border-gray-300 px-2 py-1"></td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-2 py-1">ペンション シーガル</td>
                        <td className="border border-gray-300 px-2 py-1"></td>
                        <td className="border border-gray-300 px-2 py-1">https://travel.rakuten.co.jp/...; https://www.jalan.net/...</td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-2 py-1">リゾートホテル ABC</td>
                        <td className="border border-gray-300 px-2 py-1">https://resort-abc.jp</td>
                        <td className="border border-gray-300 px-2 py-1">https://travel.rakuten.co.jp/...</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-green-700">
                  ※ B列（自社HP）は独自ドメインの公式サイトのみを抽出します<br/>
                  ※ C列（他OTAなどのサイト）は楽天、じゃらん、Booking.comなどのOTAサイトを抽出します<br/>
                  ※ 複数のOTAサイトが見つかった場合はセミコロン（;）で区切って表示します
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
