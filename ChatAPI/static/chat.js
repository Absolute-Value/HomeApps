// textareaのEnter送信・自動リサイズ処理
document.addEventListener('DOMContentLoaded', function() {
  const textarea = document.getElementById('user_input');
  if (!textarea) return;

  // Enterで送信（Shift+Enterで改行）、IME変換中は無視
  textarea.addEventListener('keydown', function(e) {
    if (e.isComposing) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      document.getElementById('send-btn').click();
    }
  });

  // 自動リサイズ（最大3行）
  textarea.addEventListener('input', function() {
    this.rows = 1;
    const lines = this.value.split('\n').length;
    this.rows = Math.min(lines, 3);
    this.style.overflowY = lines > 3 ? 'scroll' : 'auto';
  });
});
function appendMessage(content, role='assistant'){
  const chatMain = document.querySelector('.chat-main') || document.querySelector('main');
  const item = document.createElement('div');
  item.className = 'py-2 message-item' + (role === 'user' ? ' d-flex justify-content-end' : '');
  item.setAttribute('data-role', role);

  const messageContent = document.createElement('div');
  messageContent.className = 'rounded-5 p-3' + (role !== 'user' ? ' border border-dark' : '') + (role === 'user' ? ' w-auto bg-body-tertiary' : '');

  const rendered = document.createElement('div');
  rendered.className = 'rendered-markdown';

  if (role === 'user') {
    rendered.innerHTML = content.replace(/\n/g, '<br>');
  } else if (typeof marked !== 'undefined') {
    const html = marked.parse(content);
    rendered.innerHTML = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(html) : html;
  } else {
    rendered.textContent = content;
  }

  messageContent.appendChild(rendered);
  item.appendChild(messageContent);
  chatMain.appendChild(item);
  chatMain.scrollTop = chatMain.scrollHeight;
  return rendered; // 返り値でレンダリング要素を渡し、ストリーミング更新を可能にする
}

document.querySelectorAll('.message-item').forEach(item => {
  const raw = item.querySelector('.raw-markdown');
  const target = item.querySelector('.rendered-markdown');
  const role = item.getAttribute('data-role');
  if (!raw || !target) return;
  try {
    const md = raw.textContent || '';
    if (role === 'user') target.innerHTML = md.replace(/\n/g, '<br>');
    else if (typeof marked !== 'undefined') {
      const html = marked.parse(md);
      target.innerHTML = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(html) : html;
    } else target.textContent = md;
  } catch (err) {
    console.error('Error rendering saved markdown:', err);
    target.textContent = raw.textContent || '';
  } finally {
    raw.remove();
  }
});

// ページ読み込み時にメッセージエリアを最下部にスクロール
const chatMain = document.querySelector('.chat-main');
if (chatMain && chatMain.scrollHeight > chatMain.clientHeight) chatMain.scrollTop = chatMain.scrollHeight;

const chatForm = document.getElementById('chat-form');
if (chatForm) {
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('user_input');
    const model_select = document.getElementById('model_select');
    const user_input = input.value;
    if (!user_input) return;

    // ユーザーメッセージを追加し、返却された要素を使ってストリーム更新
    appendMessage(user_input, 'user');
    input.value = '';

    let path = window.location.pathname;
    if (!path.startsWith('/c/')) path = '/';

    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ user_input, model_select: model_select.value })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let assistantAccum = '';
    // まず空の assistant メッセージを追加して要素を取得
    const assistantRendered = appendMessage('', 'assistant');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      assistantAccum += chunk;

      if (typeof marked !== 'undefined') {
        const html = marked.parse(assistantAccum);
        assistantRendered.innerHTML = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(html) : html;
      } else {
        assistantRendered.textContent = assistantAccum;
      }
      chatMain.scrollTop = chatMain.scrollHeight;
    }

    try {
      const chatId = res.headers.get('X-Chat-Id');
      if (chatId) {
        window.location.href = `/c/${chatId}`;
        return;
      }
    } catch (err) {
      console.warn('Could not read X-Chat-Id header:', err);
    }
  });
}
