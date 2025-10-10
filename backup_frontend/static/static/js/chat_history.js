// Chat history sidebar logic
document.addEventListener('DOMContentLoaded', function() {
  initChatHistory();
});

function initChatHistory() {
  // Create sidebar
  const chatSidebar = document.createElement('aside');
  chatSidebar.id = 'chatSidebar';
  chatSidebar.className = 'chat-sidebar';
  chatSidebar.innerHTML = `
    <div class="chat-sidebar-header">
      <h3>Previous Chats</h3>
      <button id="closeSidebar" class="icon-btn" title="Close">✖</button>
    </div>
    <ul id="chatList" class="chat-list"></ul>
  `;
  document.body.appendChild(chatSidebar);

  // Create and add button to navbar
  const openBtn = document.createElement('button');
  openBtn.className = 'icon-btn chat-history-btn';
  openBtn.textContent = '🕑';
  openBtn.title = 'Show Previous Chats';
  openBtn.onclick = () => {
    chatSidebar.classList.add('open');
    loadChatHistory();
  };
  
  const nav = document.querySelector('.site-header .main-nav');
  if (nav) {
    nav.appendChild(openBtn);
    console.log('Chat history button added to navbar');
  } else {
    console.error('Could not find navbar to add chat history button');
  }
  
  document.getElementById('closeSidebar').onclick = () => chatSidebar.classList.remove('open');

  // Fetch and render chat history
  async function loadChatHistory() {
    try {
      const res = await fetch('/chat-history');
      const data = await res.json();
      const chatList = document.getElementById('chatList');
      chatList.innerHTML = '';
      
      if (!data.history.length) {
        chatList.innerHTML = '<li class="empty">No previous chats yet.</li>';
        return;
      }
      
      data.history.slice().reverse().forEach((chat, idx) => {
        const li = document.createElement('li');
        li.className = 'chat-item';
        li.innerHTML = `
          <div class="chat-q">Q: ${escapeHtml(chat.question)}</div>
          <div class="chat-a">A: ${escapeHtml(chat.answer)}</div>
          <div class="chat-meta">${new Date(chat.timestamp*1000).toLocaleString()} | Confidence: ${escapeHtml(chat.confidence_level)}</div>
          <button class="icon-btn chat-insert" title="Insert into chat">↩</button>
        `;
        li.querySelector('.chat-insert').onclick = () => {
          document.getElementById('questionInput').value = chat.question;
          document.getElementById('questionResults').innerHTML = `<div class='answer-block fade-in'><h4>Previous Answer</h4><p>${escapeHtml(chat.answer)}</p></div>`;
          chatSidebar.classList.remove('open');
        };
        chatList.appendChild(li);
      });
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  }

  function escapeHtml(str='') { 
    return str.replace(/[&<>"']/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c])); 
  }

  // Save chat after each Q&A
  window.saveChatToHistory = async function(chatObj) {
    try {
      await fetch('/save-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chatObj)
      });
    } catch (error) {
      console.error('Error saving chat:', error);
    }
  };
}
