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
    rendered.textContent = content;
  } else {
    // assistant may contain markdown/html
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
      console.log('Rendering saved message, role=', role, 'md=', md.slice(0,80));
      if (role === 'user') {
        target.textContent = md;
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

document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('user_input');
  const user_input = input.value;
  if(!user_input) return;

  appendMessage(user_input, 'user');
  input.value = '';

  let path = window.location.pathname;
  if(!path.startsWith('/c/')) path = '/';

  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ user_input })
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let assistantAccum = '';
  let tempChatId = null;
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
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop(); // remainder
    for(const part of parts){
      if(!part.trim()) continue;
      const lines = part.split('\n').map(l => l.replace(/^data:\s?/, ''));
      const data = lines.join('\n');
      try{
        const parsed = JSON.parse(data);
        if(parsed.event === 'meta' && parsed.chat_id){
          tempChatId = parsed.chat_id;
          history.replaceState(null, '', '/c/' + tempChatId);
        }
        continue;
      }catch(_){
        // not JSON, treat as chunk text
      }
      assistantAccum += data;
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
  }

  window.location.reload();
});
