// textareaのEnter送信・自動リサイズ処理
document.addEventListener('DOMContentLoaded', function() {
  const textarea = document.getElementById('user_input');
  if (textarea) {
    textarea.addEventListener('keydown', function(e) {
      // IME変換中は送信しない
      if (e.isComposing) return;
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        document.getElementById('send-btn').click();
      }
    });
    textarea.addEventListener('input', function() {
      this.rows = 1;
      const lines = this.value.split('\n').length;
      this.rows = Math.min(lines, 3);
      this.style.overflowY = lines > 3 ? 'scroll' : 'auto';
    });
  }
});
function appendMessage(content, role='assistant'){
  const chatMain = document.querySelector('.chat-main') || document.querySelector('main');

  // Build the same structure as server-rendered messages to avoid layout differences
  const item = document.createElement('div');
  item.className = 'container py-2 message-item' + (role === 'user' ? ' d-flex justify-content-end' : '');
  item.setAttribute('data-role', role);

  const messageContent = document.createElement('div');
  messageContent.className = 'message-content rounded-5 p-3' + 
    (role !== 'user' ? ' border border-dark' : '') + 
    (role === 'user' ? ' w-auto bg-body-tertiary' : '');

  const rendered = document.createElement('div');
  rendered.className = 'rendered-markdown';

  if(role === 'user'){
    rendered.innerHTML = content.replace(/\n/g, '<br>');
  } else {
    const md = content;
    if (typeof marked !== 'undefined') {
      const html = marked.parse(md);
      const safe = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(html) : html;
      rendered.innerHTML = safe;
    } else {
      const p = document.createElement('p');
      p.className = 'card-text';
      p.textContent = md;
      rendered.appendChild(p);
    }
  }

  messageContent.appendChild(rendered);
  item.appendChild(messageContent);
  chatMain.appendChild(item);
  chatMain.scrollTop = chatMain.scrollHeight;
}

// On initial load, render any saved raw markdown blocks
document.querySelectorAll('.message-item').forEach(item => {
  const raw = item.querySelector('.raw-markdown');
  const target = item.querySelector('.rendered-markdown');
  const role = item.getAttribute('data-role');
  if(raw && target){
    try {
      const md = raw.textContent || '';
      if (role === 'user') {
        target.innerHTML = md.replace(/\n/g, '<br>');
      } else if (typeof marked !== 'undefined') {
        const html = marked.parse(md);
        const safe = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(html) : html;
        if (safe && safe.trim()) {
          target.innerHTML = safe;
        } else {
          target.textContent = md;
        }
      } else {
        target.textContent = md;
      }
    } catch (err) {
      console.error('Error rendering saved markdown:', err);
      target.textContent = raw.textContent || '';
    } finally {
      raw.remove();
    }
  }
});

// ページ読み込み時にメッセージエリアを最下部にスクロール
const chatMain = document.querySelector('.chat-main');
if (chatMain && chatMain.scrollHeight > chatMain.clientHeight) {
  chatMain.scrollTop = chatMain.scrollHeight;
}

const chatForm = document.getElementById('chat-form');
if (chatForm) {
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('user_input');
    const model_select = document.getElementById('model_select');
    const user_input = input.value;
    if(!user_input) return;

    appendMessage(user_input, 'user');
    input.value = '';

    let path = window.location.pathname;
    if(!path.startsWith('/c/')) path = '/';

    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ 
        user_input,
        model_select: model_select.value
      })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let assistantAccum = '';
    const assistantContainer = document.createElement('div');
    assistantContainer.className = 'container';
    assistantContainer.innerHTML = `
      <div class="message-content rounded-5 p-3 border border-dark">
        <p id="assistant-stream"></p>
      </div>`;
    const chatMain = document.querySelector('.chat-main') || document.querySelector('main');
    chatMain.appendChild(assistantContainer);
    const assistantNode = document.getElementById('assistant-stream');

    while(true){
      const { done, value } = await reader.read();
      if(done) break;
      const chunk = decoder.decode(value, { stream: true });

      assistantAccum += chunk;
      if (typeof marked !== 'undefined') {
        const html = marked.parse(assistantAccum);
        if (typeof DOMPurify !== 'undefined') {
          assistantNode.innerHTML = DOMPurify.sanitize(html);
        } else {
          assistantNode.innerHTML = html;
        }
      } else {
        assistantNode.textContent = assistantAccum;
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
