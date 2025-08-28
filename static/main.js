// 状態
let history = []; // 例: ["あめ", "めだか", ...]
let left = 20;
let nextHead = null;

const elWord = document.getElementById('word');
const elSend = document.getElementById('send');
const elReset = document.getElementById('reset');
const elList = document.getElementById('list');
const elMsg = document.getElementById('msg');
const elNext = document.getElementById('next');
const elLeft = document.getElementById('left');

function isHiragana(str){
  return /^[ぁ-ゖー]+$/.test(str);
}

function addItem(text){
  const li = document.createElement('li');
  li.textContent = text;
  elList.appendChild(li);
}

function resetGame(){
  history = [];
  left = 20;
  nextHead = null;
  elList.innerHTML = '';
  elMsg.textContent = '';
  elNext.textContent = 'はじめは なんでも いいよ';
  elLeft.textContent = String(left);
  elWord.value = '';
  elWord.disabled = false; elSend.disabled = false;
  elWord.focus();
}

async function sendWord(){
  const w = (elWord.value || '').trim();
  if(!w){ elMsg.textContent = 'ことばを入れてね'; return; }
  if(!isHiragana(w)){ elMsg.textContent = 'ひらがなだけで入れてね'; return; }
  if(left <= 0){ elMsg.textContent = '今日はここまで！'; return; }

  try{
    const res = await fetch('/api/ai_move', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ history, user_word: w })
    });
    const data = await res.json();

    if(!data.ok){
      // ルール違反など → ユーザー負け
      if(data.user_word){ addItem('あなた: ' + data.user_word); }
      elMsg.textContent = data.message || 'おしまい';
      elWord.disabled = true; elSend.disabled = true;
      return;
    }

    // 正常: ユーザー語 → AI語
    addItem('あなた: ' + data.user_word);
    history.push(data.user_word);
    left = 20 - data.turn_count; // サーバーのカウントに合わせる
    elLeft.textContent = String(Math.max(0, left));

    if(data.ai_word){
      addItem('AI: ' + data.ai_word);
      history.push(data.ai_word);
      nextHead = data.next_head_for_user || null;
      elNext.textContent = nextHead ? `つぎは『${nextHead}』からはじめてね` : 'はじめは なんでも いいよ';
    }

    elMsg.textContent = data.message || '';

    if(data.game_over){
      elWord.disabled = true; elSend.disabled = true;
    } else {
      elWord.value = '';
      elWord.focus();
    }
  } catch(e){
    console.error(e);
    elMsg.textContent = 'サーバーにつながらないよ…';
  }
}

elSend.addEventListener('click', sendWord);
elWord.addEventListener('keydown', (ev)=>{ if(ev.key==='Enter') sendWord(); });
elReset.addEventListener('click', resetGame);

resetGame();
