# AIしりとり（FastAPI + Gemini）

ひらがなだけであそぶ しりとりです。AI とたいせんできます。

## あそびかた（かんたん）
- ことばを ひらがなで いれて「おくる」を おします。
- AI が つづけて ことばを だします。
- 20かい あそべます。
- 「ん」で おわると まけです。おなじ ことばは つかえません。

---

## セットアップ（Windows）
1. このフォルダを作業場所にしてください（おすすめ）:
   `C:\\Users\\s240017\\CascadeProjects\\ai-shiritori`
2. Python をインストール（3.10+ 推奨）。
3. 仮想環境（お好みで）:
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. 依存インストール:
   ```powershell
   pip install -r requirements.txt
   ```
5. Gemini API キーを環境変数に設定（Google AI Studio で取得）:
   ```powershell
   setx GEMINI_API_KEY "あなたの_API_キー"
   # 新しいターミナルを開くと反映されます
   ```

## ローカル起動
```powershell
uvicorn app.main:app --reload
```
開いたら: http://127.0.0.1:8000/

## プロジェクト構成
```
ai-shiritori/
├─ app/
│  ├─ main.py          # FastAPI 本体（API, 静的配信, Gemini 連携）
│  └─ shiritori.py     # しりとりのルール
├─ static/
│  ├─ index.html       # 画面
│  ├─ style.css        # 見た目
│  └─ main.js          # うごき
├─ requirements.txt
├─ render.yaml         # Render 用設定
└─ README.md
```

## Render にデプロイ
1. GitHub リポジトリを作成し、このフォルダを push します。
2. https://render.com にログイン → New+ → Web Service。
3. リポジトリを選び、環境変数に `GEMINI_API_KEY` を追加。
4. デプロイすると URL が発行されます。

## 備考
- モデルは既定で `gemini-1.5-flash` を使います。変更は環境変数 `GEMINI_MODEL`。
- API はステートレスです。履歴はフロントから送っています。
- モデル出力がルールに合わない時は、簡易辞書でフォールバックします。
