# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import random
from typing import List, Optional, Set

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from .shiritori import (
    to_hiragana,
    validate_user_move,
    validate_ai_move,
    next_required_head,
)

# .env を読み込む（存在すれば）
load_dotenv()

# Gemini API
try:
    import google.generativeai as genai
except Exception:
    genai = None

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if genai and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 簡易フォールバック辞書（必要最低限）
FALLBACK_DICT = {
    "あ": ["あり", "あめ", "あさ"],
    "い": ["いぬ", "いけ", "いか"],
    "う": ["うし", "うみ", "うた"],
    "え": ["えび", "えき", "えのぐ"],
    "お": ["おに", "おか", "おゆ"],
    "か": ["かめ", "かさ", "からす"],
    "き": ["きつね", "きのこ", "きりん"],
    "く": ["くま", "くき", "くるま"],
    "け": ["けむし", "けしき", "けが"],
    "こ": ["ことり", "こめ", "こおり"],
    "さ": ["さかな", "さる", "さくら"],
    "し": ["しろ", "しお", "しんぶん"],
    "す": ["すいか", "すずめ", "すな"],
    "せ": ["せみ", "せかい", "せんべい"],
    "そ": ["そら", "そば", "そり"],
    "た": ["たまご", "たに", "たこ"],
    "ち": ["ちず", "ちから", "ちくわ"],
    "つ": ["つき", "つばさ", "つち"],
    "て": ["てがみ", "てぶくろ", "てんぷら"],
    "と": ["とら", "とけい", "とまと"],
    "な": ["なす", "なべ", "なみ"],
    "に": ["にわ", "にく", "にじ"],
    "ぬ": ["ぬいぐるみ", "ぬの", "ぬま"],
    "ね": ["ねこ", "ねぎ", "ねずみ"],
    "の": ["のり", "のはら", "のこぎり"],
    "は": ["はさみ", "はな", "はっぱ"],
    "ひ": ["ひこうき", "ひつじ", "ひみつ"],
    "ふ": ["ふね", "ふく", "ふとん"],
    "へ": ["へび", "へや", "へいたい"],
    "ほ": ["ほし", "ほね", "ほたる"],
    "ま": ["まくら", "まめ", "まど"],
    "み": ["みず", "みかん", "みち"],
    "む": ["むし", "むぎ", "むね"],
    "め": ["めがね", "めだか", "めんたいこ"],
    "も": ["もも", "もり", "もち"],
    "や": ["やま", "やさい", "やぎ"],
    "ゆ": ["ゆき", "ゆめ", "ゆび"],
    "よ": ["ようふく", "よる", "よこ"],
    "ら": ["らっこ", "らっぱ", "らいおん"],
    "り": ["りす", "りんご", "りょうり"],
    "る": ["るす", "るつぼ", "るーれっと"],
    "れ": ["れいぞうこ", "れもん", "れんこん"],
    "ろ": ["ろうそく", "ろぼっと", "ろてんぶろ"],
    "わ": ["わに", "わごむ", "わた"],
}

MAX_TURNS = 20  # ユーザーの入力回数の上限

class MoveRequest(BaseModel):
    history: List[str] = []  # 交互の単語配列（古い→新しい）
    user_word: str

class MoveResponse(BaseModel):
    ok: bool
    message: str
    user_word: Optional[str] = None
    ai_word: Optional[str] = None
    next_head_for_user: Optional[str] = None
    used: List[str] = []
    turn_count: int = 0  # ユーザーの入力回数
    game_over: bool = False
    winner: Optional[str] = None  # "user" | "ai" | "none"

app = FastAPI(title="AIしりとり")

# CORS（開発用に広めに許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル（フロント）
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def root_index():
        index_path = os.path.join(static_dir, "index.html")
        return FileResponse(index_path)

def _turn_count_from_history(history: List[str]) -> int:
    # ユーザーが先手前提: 偶数インデックスがユーザー
    return (len(history) + 1) // 2


def _choose_fallback(head: str, used: Set[str]) -> Optional[str]:
    candidates = [w for w in FALLBACK_DICT.get(head, []) if w not in used]
    return random.choice(candidates) if candidates else None


def _gemini_generate(required_head: str, used: Set[str], last_word: Optional[str]) -> Optional[str]:
    if not (genai and GEMINI_API_KEY):
        return None
    sys_rules = (
        "あなたは日本語のしりとりAIです。ルールを厳守してください:\n"
        "- ひらがなだけで1語だけを出力する（余計な文字や説明を一切書かない）\n"
        "- 先頭文字は『{h}』から始める\n"
        "- 過去に出た言葉は使わない\n"
        "- 語尾を『ん』で終わらせない\n"
        "- 語尾が小さい文字や長音（ー）のときは、しりとり上の次の先頭文字を正しく意識する\n"
    ).format(h=required_head)

    examples = "、".join(sorted(list(used))[-5:]) if used else "なし"
    user_msg = (
        f"これまでのことば: {examples}\n"
        f"最後のことば: {last_word or 'なし'}\n"
        f"次は『{required_head}』からはじまることばを1語だけ、ひらがなで書いてね。"
    )

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content([
            {"role": "user", "parts": [sys_rules + "\n\n" + user_msg]},
        ])
        candidate = resp.text.strip() if getattr(resp, "text", None) else None
        if candidate:
            candidate = candidate.split()[0].strip()
        return candidate
    except Exception:
        return None


@app.post("/api/ai_move", response_model=MoveResponse)
def ai_move(req: MoveRequest):
    history = [to_hiragana(w) for w in req.history if w]
    used: Set[str] = set(history)

    # ターン上限チェック（入力前）
    user_turns_before = _turn_count_from_history(history)
    if user_turns_before >= MAX_TURNS:
        return MoveResponse(
            ok=False,
            message="20かいまでだよ。さいしょからやりなおしてね",
            used=list(used),
            turn_count=user_turns_before,
            game_over=True,
            winner="none",
        )

    # 期待先頭文字
    expected_head: Optional[str] = None
    if history:
        expected_head = next_required_head(history[-1])

    # ユーザー入力検証
    ok, msg = validate_user_move(req.user_word, expected_head, used)
    w_user = to_hiragana(req.user_word)
    if not ok:
        # ルール違反はユーザーの負け
        return MoveResponse(
            ok=False,
            message=msg,
            user_word=w_user,
            used=list(used),
            turn_count=user_turns_before + 1,
            game_over=True,
            winner="ai",
        )

    # ユーザー語を追加
    history.append(w_user)
    used.add(w_user)

    # 次の先頭（AI用）
    head = next_required_head(w_user)
    if head is None:
        raise HTTPException(status_code=400, detail="単語が空です")

    # Gemini で生成
    ai_word: Optional[str] = _gemini_generate(head, used, w_user)

    # 検証と再試行（1回）
    if ai_word:
        ok_ai, _ = validate_ai_move(ai_word, head, used)
        if not ok_ai:
            # 1回だけ再試行
            ai_word = _gemini_generate(head, used, w_user)

    # フォールバック
    if not ai_word:
        ai_word = _choose_fallback(head, used)

    # なお検証
    if not ai_word:
        # 返せない場合はユーザーの勝ち
        return MoveResponse(
            ok=True,
            message="AIはこたえられなかったよ。あなたのかち！",
            user_word=w_user,
            used=list(used),
            turn_count=user_turns_before + 1,
            game_over=True,
            winner="user",
        )

    ok_ai, msg_ai = validate_ai_move(ai_word, head, used)
    if not ok_ai:
        # 不正ならユーザーの勝ち
        return MoveResponse(
            ok=True,
            message="AIがルールをまもれなかったよ。あなたのかち！",
            user_word=w_user,
            ai_word=ai_word,
            used=list(used),
            turn_count=user_turns_before + 1,
            game_over=True,
            winner="user",
        )

    # 採用
    history.append(ai_word)
    used.add(ai_word)

    # 次のユーザーの頭文字
    next_head = next_required_head(ai_word)

    # ターン上限チェック（入力後）
    user_turns_after = _turn_count_from_history(history)
    game_over = user_turns_after >= MAX_TURNS
    winner = None
    end_msg = ""
    if game_over:
        end_msg = "きょうはここまで！またあしたあそぼうね"

    return MoveResponse(
        ok=True,
        message=end_msg or f"つぎは『{next_head}』からはじめてね",
        user_word=w_user,
        ai_word=ai_word,
        next_head_for_user=next_head,
        used=list(used),
        turn_count=user_turns_after,
        game_over=game_over,
        winner="none" if game_over else None,
    )
