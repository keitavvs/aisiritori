# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import List, Tuple, Optional, Set

# ひらがな・カタカナ・長音符などの扱い
_HIRAGANA_RANGE = re.compile(r"^[ぁ-ゖー]+$")
# 小さいかな -> 大きいかな 対応表
_SMALL_TO_LARGE = {
    "ぁ": "あ", "ぃ": "い", "ぅ": "う", "ぇ": "え", "ぉ": "お",
    "っ": "つ", "ゃ": "や", "ゅ": "ゆ", "ょ": "よ",
    "ゎ": "わ",
}
# 濁点・半濁点の正規化: ひらがな範囲ではそのまま扱う（最終文字の大小のみ調整）

# カタカナ -> ひらがな 変換
_KATAKANA_TO_HIRAGANA_OFFSET = ord("ぁ") - ord("ァ")

def to_hiragana(s: str) -> str:
    """入力をひらがなのみに正規化。
    - 全角カタカナはひらがなへ
    - 全角英数や記号は除去
    - 全角スペース・半角スペースは除去
    - 半角カナは対象外（できるだけ除去）
    - 小さい文字はそのまま保持（終端処理でのみ大きくする）
    """
    out = []
    for ch in s.strip():
        code = ord(ch)
        # スペース類はスキップ
        if ch.isspace():
            continue
        # 長音・ひらがな
        if 'ぁ' <= ch <= 'ゖ' or ch == 'ー':
            out.append(ch)
            continue
        # カタカナ -> ひらがな
        if 'ァ' <= ch <= 'ヺ' or ch == 'ー':
            if ch == 'ー':
                out.append(ch)
            else:
                out.append(chr(code + _KATAKANA_TO_HIRAGANA_OFFSET))
            continue
        # その他は無視
    return "".join(out)


def is_hiragana_only(s: str) -> bool:
    return bool(_HIRAGANA_RANGE.match(s))


def strip_trailing_prolong_mark(s: str) -> str:
    """語尾の長音記号を取り除く（末尾がーなら無視して1つ前を見る）。"""
    return s[:-1] if s.endswith("ー") else s


def normalize_last_char(s: str) -> Optional[str]:
    """しりとりの語尾判定用に末尾かなを取得。
    - 末尾が長音「ー」なら、その直前の文字を対象
    - 末尾が小さい文字なら大きい文字に正規化
    - 末尾が存在しなければ None
    """
    if not s:
        return None
    t = strip_trailing_prolong_mark(s)
    if not t:
        return None
    last = t[-1]
    return _SMALL_TO_LARGE.get(last, last)


def violates_end_n(s: str) -> bool:
    """末尾が「ん」か判定（長音を除去した上で判定）。"""
    t = strip_trailing_prolong_mark(s)
    return t.endswith("ん") if t else False


def validate_user_move(user_word: str, expected_head: Optional[str], used: Set[str]) -> Tuple[bool, str]:
    """ユーザー入力の検証。
    - ひらがなのみ
    - 既出語でない
    - 末尾「ん」でない
    - （必要なら）先頭が expected_head と一致
    戻り値: (OKか, メッセージ)
    """
    w = to_hiragana(user_word)
    if not w:
        return False, "ことばを入力してね"
    if not is_hiragana_only(w):
        return False, "ひらがなだけで入力してね"
    if w in used:
        return False, "同じことばは使えないよ"
    if violates_end_n(w):
        return False, "『ん』で終わったのでまけだよ"
    if expected_head:
        head = w[0]
        # 小さい文字開始の場合は大きく
        head = _SMALL_TO_LARGE.get(head, head)
        if head != expected_head:
            return False, f"『{expected_head}』からはじめてね"
    return True, "OK"


def validate_ai_move(ai_word: str, required_head: str, used: Set[str]) -> Tuple[bool, str]:
    w = to_hiragana(ai_word)
    if not w or not is_hiragana_only(w):
        return False, "AIのことばがひらがなじゃないよ"
    # 先頭一致
    head = _SMALL_TO_LARGE.get(w[0], w[0])
    if head != required_head:
        return False, "AIの先頭文字が合っていないよ"
    if w in used:
        return False, "AIが同じことばを使ったよ"
    if violates_end_n(w):
        return False, "AIが『ん』で終わったよ"
    return True, "OK"


def next_required_head(word: str) -> Optional[str]:
    last = normalize_last_char(word)
    return last


def summarize_history(words: List[str]) -> str:
    return " → ".join(words)

