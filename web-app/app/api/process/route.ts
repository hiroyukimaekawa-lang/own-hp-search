import { NextRequest, NextResponse } from 'next/server';
import csv from 'csv-parser';
import { Readable } from 'stream';

// OTAドメインリスト
const OTA_DOMAINS = [
  'jalan.net',
  'rakuten.co.jp',
  'booking.com',
  'agoda.com',
  'ikyu.com',
  'expedia.com',
  'expedia.co.jp',
];

// SNS・その他除外ドメインリスト（航空会社、予約サイトなど）
const EXCLUDED_DOMAINS = [
  'instagram.com',
  'facebook.com',
  'twitter.com',
  'x.com',
  'ameblo.jp',
  'fc2.com',
  'jimdo.com',
  'wixsite.com',
  'google.com',
  'jal.co.jp', // JAL予約サイト
  'ana.co.jp', // ANA予約サイト
  'japanican.com', // ジャパニカン
  'relux.com', // るるぶトラベル
  'yadoplace.com', // やどぷら
];

// 検索クエリのパターン
const SEARCH_QUERIES = [
  (name: string) => `${name} 公式サイト`,
  (name: string) => `${name} 宿`,
  (name: string) => `${name} ホームページ`,
];

interface Facility {
  屋号: string;
  自社HP?: string;
  他OTAなどのサイト?: string;
}

/**
 * Brave Search APIで検索を実行
 */
async function searchBraveAPI(query: string, apiKey: string): Promise<any> {
  try {
    const response = await fetch(
      `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=10`,
      {
        headers: {
          'Accept': 'application/json',
          'X-Subscription-Token': apiKey,
        },
      }
    );

    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error(`検索エラー (${query}):`, error);
    return null;
  }
}

/**
 * URLからドメインを抽出
 */
function extractDomain(url: string): string {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace('www.', '').toLowerCase();
  } catch {
    return '';
  }
}

/**
 * OTAドメインかどうかを判定
 */
function isOTADomain(url: string): boolean {
  const domain = extractDomain(url);
  return OTA_DOMAINS.some((ota) => domain.includes(ota));
}

/**
 * 除外ドメインかどうかを判定
 */
function isExcludedDomain(url: string): boolean {
  const domain = extractDomain(url);
  return EXCLUDED_DOMAINS.some((excluded) => domain.includes(excluded));
}

/**
 * 検索結果から自社HPとOTAサイトを分けて抽出（厳格な判定）
 */
function extractSites(
  searchResults: any,
  facilityName: string = ''
): { officialSite: string | null; otaSites: string[] } {
  const result = {
    officialSite: null as string | null,
    otaSites: [] as string[],
  };

  if (!searchResults || !searchResults.web || !searchResults.web.results) {
    return result;
  }

  const results = searchResults.web.results;
  const facilityNameLower = facilityName.toLowerCase().replace(/[\s　]/g, '');

  for (const item of results) {
    const url = item.url;
    const title = item.title || '';
    const description = item.description || '';

    if (!url) continue;

    // SNS・その他除外ドメインをスキップ
    if (isExcludedDomain(url)) {
      continue;
    }

    // OTAドメインかチェック
    if (isOTADomain(url)) {
      // OTAサイトを追加（重複を避ける）
      if (!result.otaSites.includes(url)) {
        result.otaSites.push(url);
      }
      continue;
    }

    // 自社HPの厳格な判定
    // 1. タイトルや説明文に「公式」「オフィシャル」が含まれるか
    const textToCheck = (title + ' ' + description).toLowerCase();
    const hasOfficialKeyword =
      textToCheck.includes('公式') ||
      textToCheck.includes('オフィシャル') ||
      textToCheck.includes('official');

    // 2. 施設名がドメインやURLに含まれているか（簡易チェック）
    const domain = extractDomain(url);
    let hasFacilityName = false;
    if (facilityNameLower) {
      // 施設名の主要部分（最初の5文字）がドメインに含まれるか
      const facilityKeywords = [
        facilityNameLower.substring(0, Math.min(5, facilityNameLower.length)),
        facilityNameLower
          .replace('ペンション', '')
          .replace('民宿', '')
          .replace('ホテル', '')
          .trim()
          .substring(0, Math.min(5, facilityNameLower.length)),
      ];
      for (const keyword of facilityKeywords) {
        if (keyword.length >= 3 && domain.includes(keyword)) {
          hasFacilityName = true;
          break;
        }
      }
    }

    // 自社HPとして採用する条件（厳格）
    // 条件1: 「公式」「オフィシャル」キーワードがある
    // 条件2: 施設名がドメインに含まれている
    // どちらか一方でも満たせば自社HPと判定
    if (hasOfficialKeyword || hasFacilityName) {
      if (!result.officialSite) {
        result.officialSite = url;
      }
    }
    // どちらの条件も満たさない場合は、OTAサイトとして扱わずにスキップ
    // （自社HPとして採用しない）
  }

  return result;
}

/**
 * 屋号から自社HPとOTAサイトを検索
 */
async function searchSites(
  facilityName: string,
  apiKey: string
): Promise<{ officialSite: string | null; otaSites: string[] }> {
  let bestResult = {
    officialSite: null as string | null,
    otaSites: [] as string[],
  };

  // 各検索クエリを順番に試す
  for (const queryFunc of SEARCH_QUERIES) {
    const query = queryFunc(facilityName);
    const searchResults = await searchBraveAPI(query, apiKey);
    const extracted = extractSites(searchResults, facilityName);

    // 自社HPが見つかった場合は終了
    if (extracted.officialSite) {
      return {
        officialSite: extracted.officialSite,
        otaSites: [...bestResult.otaSites, ...extracted.otaSites],
      };
    }

    // OTAサイトを蓄積
    bestResult.otaSites = [...bestResult.otaSites, ...extracted.otaSites];

    // API制限を考慮して少し待機
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  // OTAサイトの重複を除去
  bestResult.otaSites = Array.from(new Set(bestResult.otaSites));

  return bestResult;
}

/**
 * CSVをパース
 */
async function parseCSV(file: File): Promise<Facility[]> {
  return new Promise(async (resolve, reject) => {
    try {
      const facilities: Facility[] = [];
      const arrayBuffer = await file.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);
      const stream = Readable.from(buffer);

      stream
        .pipe(csv())
        .on('data', (row) => {
          const name = row['屋号'] || row['屋号 '] || Object.values(row)[0];
          if (name) {
            facilities.push({ 屋号: String(name).trim() });
          }
        })
        .on('end', () => {
          resolve(facilities);
        })
        .on('error', (error) => {
          reject(error);
        });
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * CSVを生成
 */
function generateCSV(facilities: Facility[]): string {
  const header = '屋号,自社HP,他OTAなどのサイト\n';
  const rows = facilities.map((facility) => {
    const name = facility.屋号.replace(/,/g, '，'); // CSVのカンマを全角に変換
    const officialSite = facility.自社HP || '';
    const otaSites = facility.他OTAなどのサイト || '';
    return `${name},${officialSite},${otaSites}`;
  });
  return header + rows.join('\n');
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    const apiKey = (formData.get('apiKey') as string) || process.env.BRAVE_API_KEY || '';

    if (!file) {
      return NextResponse.json({ error: 'ファイルがアップロードされていません' }, { status: 400 });
    }

    if (!apiKey) {
      return NextResponse.json({ error: 'APIキーが設定されていません' }, { status: 400 });
    }

    // CSVをパース
    const facilities = await parseCSV(file);

    if (facilities.length === 0) {
      return NextResponse.json({ error: 'CSVファイルにデータがありません' }, { status: 400 });
    }

    // 各施設について検索
    const results: Facility[] = [];
    for (let i = 0; i < facilities.length; i++) {
      const facility = facilities[i];
      console.log(`処理中: ${i + 1}/${facilities.length} - ${facility.屋号}`);

      try {
        const sites = await searchSites(facility.屋号, apiKey);
        results.push({
          屋号: facility.屋号,
          自社HP: sites.officialSite || undefined,
          他OTAなどのサイト: sites.otaSites.length > 0 ? sites.otaSites.join('; ') : undefined,
        });
      } catch (error) {
        console.error(`エラー (${facility.屋号}):`, error);
        // エラーが起きても処理を続ける
        results.push({
          屋号: facility.屋号,
          自社HP: undefined,
          他OTAなどのサイト: undefined,
        });
      }

      // API制限を考慮して待機（最後の1件は不要）
      if (i < facilities.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }

    // CSVを生成
    const csvContent = generateCSV(results);

    return NextResponse.json({
      csv: csvContent,
      count: results.length,
    });
  } catch (error) {
    console.error('エラー:', error);
    return NextResponse.json(
      { error: '処理中にエラーが発生しました: ' + (error as Error).message },
      { status: 500 }
    );
  }
}

