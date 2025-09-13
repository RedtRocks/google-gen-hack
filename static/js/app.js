// Frontend interaction logic
(() => {
  const analyzeForm = document.getElementById('analyzeForm');
  const resultsSection = document.getElementById('resultsSection');
  const qaSection = document.getElementById('qaSection');
  const questionForm = document.getElementById('questionForm');
  const questionInput = document.getElementById('questionInput');
  const questionResults = document.getElementById('questionResults');
  const fileInput = document.getElementById('fileInput');
  const textInput = document.getElementById('textInput');
  const themeToggle = document.getElementById('themeToggle');
  const loadingDialog = document.getElementById('loadingDialog');
  const loadingText = document.getElementById('loadingText');
  const resetBtn = document.getElementById('resetBtn');
  let currentDocumentId = null;
  let submittedDocumentText = null;

  function showLoading(msg = 'Working…') {
    loadingText.textContent = msg;
    if (!loadingDialog.open) loadingDialog.showModal();
  }
  function hideLoading() { if (loadingDialog.open) loadingDialog.close(); }

  function renderAnalysis(data) {
    const html = `
      <div class="analysis-block fade-in">
        <h3>Summary</h3>
        <p>${escapeHtml(data.summary)}</p>
      </div>
      <div class="analysis-block fade-in">
        <h3>Key Points</h3>
        <ul>${data.key_points.map(li => `<li>${escapeHtml(li)}</li>`).join('')}</ul>
      </div>
      <div class="analysis-block block-risk fade-in">
        <h3>Risks & Concerns</h3>
        <ul>${data.risks_and_concerns.map(li => `<li>${escapeHtml(li)}</li>`).join('')}</ul>
      </div>
      <div class="analysis-block block-recommend fade-in">
        <h3>Recommendations</h3>
        <ul>${data.recommendations.map(li => `<li>${escapeHtml(li)}</li>`).join('')}</ul>
      </div>
      <div class="analysis-block fade-in">
        <h3>In Simple Terms</h3>
        <p>${escapeHtml(data.simplified_explanation)}</p>
      </div>`;
    resultsSection.innerHTML = html;
    resultsSection.hidden = false;
    qaSection.hidden = false;
    resetBtn.hidden = false;
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function escapeHtml(str='') { return str.replace(/[&<>"]+/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  analyzeForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if(!fileInput.files[0] && !textInput.value.trim()) {
      alert('Upload a file or paste text.');
      return;
    }
    showLoading('Analyzing document…');
    try {
      let response;
      if (fileInput.files[0]) {
        const fd = new FormData();
        fd.append('file', fileInput.files[0]);
        fd.append('document_type', document.getElementById('documentType').value);
        fd.append('user_role', document.getElementById('userRole').value);
        fd.append('complexity_level', document.getElementById('complexityLevel').value);
        response = await fetch('/analyze-document', { method:'POST', body: fd });
        submittedDocumentText = textInput.value.trim() || 'Uploaded file';
      } else {
        submittedDocumentText = textInput.value.trim();
        response = await fetch('/analyze-text', {
          method:'POST',
            headers:{ 'Content-Type':'application/json' },
            body: JSON.stringify({
              text: submittedDocumentText,
              document_type: document.getElementById('documentType').value,
              user_role: document.getElementById('userRole').value,
              complexity_level: document.getElementById('complexityLevel').value
            })
        });
      }
      const data = await response.json();
      if(!response.ok) throw new Error(data.detail || 'Analysis failed');
      currentDocumentId = data.document_id;
      renderAnalysis(data);
      hideLoading();
    } catch(err) {
      hideLoading();
      resultsSection.hidden = false;
      resultsSection.innerHTML = `<div class='analysis-block block-risk'><h3>Error</h3><p>${escapeHtml(err.message)}</p></div>`;
    }
  });

  questionForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = questionInput.value.trim();
    if(!q) return;
    questionResults.innerHTML = '<div class="answer-block"><p>Thinking…</p></div>';
    try {
      const payload = { question: q };
      if(currentDocumentId) payload.document_id = currentDocumentId; else payload.document_text = submittedDocumentText || '';
      const res = await fetch('/ask-question', {
        method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(payload)
      });
      const data = await res.json();
      if(!res.ok) throw new Error(data.detail || 'Question failed');
      questionResults.innerHTML = `
        <div class="answer-block fade-in">
          <h4>Answer</h4>
          <p>${escapeHtml(data.answer)}</p>
          <h4>Relevant Sections</h4>
          <ul>${data.relevant_sections.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>
          <p><span class="status-chip">Confidence: ${escapeHtml(data.confidence_level)}</span></p>
        </div>`;
      questionInput.value='';
      // Save chat to history
      window.saveChatToHistory && window.saveChatToHistory({
        question: q,
        answer: data.answer,
        relevant_sections: data.relevant_sections,
        confidence_level: data.confidence_level
      });
    } catch(err) {
      questionResults.innerHTML = `<div class='answer-block'><h4>Error</h4><p>${escapeHtml(err.message)}</p></div>`;
    }
  });

  resetBtn?.addEventListener('click', () => {
    analyzeForm.reset();
    resultsSection.hidden = true; qaSection.hidden = true; questionResults.innerHTML=''; currentDocumentId=null; submittedDocumentText=null; resetBtn.hidden = true;
    window.scrollTo({ top:0, behavior:'smooth' });
  });

  // Theme toggle
  const root = document.documentElement;
  const storedTheme = localStorage.getItem('theme');
  if(storedTheme) root.setAttribute('data-theme', storedTheme);
  themeToggle?.addEventListener('click', () => {
    const current = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', current);
    localStorage.setItem('theme', current);
    themeToggle.textContent = current === 'dark' ? '🌙' : '☀️';
  });

  // Chat history functionality - load on page load
  const chatHistoryList = document.getElementById('chatHistoryList');
  if (chatHistoryList) {
    loadChatHistory();
  }
  // Clear history button
  const clearHistoryBtn = document.getElementById('clearHistory');
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', () => {
      if (confirm('Clear all chat history?')) {
        clearChatHistory();
      }
    });
  }
})();

// Global chat history functions
window.saveChatToHistory = function(chatData) {
  fetch('/save-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(chatData)
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      loadChatHistory(); // Refresh the chat history display
    }
  })
  .catch(error => {
    console.error('Error saving chat:', error);
  });
};

function loadChatHistory() {
  const chatHistoryList = document.getElementById('chatHistoryList');
  if (!chatHistoryList) return;
  
  fetch('/chat-history')
    .then(response => response.json())
    .then(data => {
      if (data.chats && data.chats.length > 0) {
        chatHistoryList.innerHTML = data.chats.map((chat, index) => `
          <li class="chat-history-item" onclick="insertChatToForm('${escapeHtml(chat.question)}')">
            <div class="chat-q">${escapeHtml(chat.question)}</div>
            <div class="chat-a">${escapeHtml(chat.answer)}</div>
            <div class="chat-meta">
              <span>${new Date(chat.timestamp).toLocaleString()}</span>
              <span>${escapeHtml(chat.confidence_level || 'Medium')}</span>
            </div>
          </li>
        `).join('');
      } else {
        chatHistoryList.innerHTML = '<div class="empty-state">No chat history yet</div>';
      }
    })
    .catch(error => {
      console.error('Error loading chat history:', error);
      chatHistoryList.innerHTML = '<div class="empty-state">Error loading chat history</div>';
    });
}

function insertChatToForm(question) {
  const questionInput = document.getElementById('questionInput');
  if (questionInput) {
    questionInput.value = question;
    questionInput.focus();
    questionInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function clearChatHistory() {
  fetch('/clear-chat-history', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        loadChatHistory(); // Refresh the display
      }
    })
    .catch(error => {
      console.error('Error clearing chat history:', error);
    });
}

function escapeHtml(str='') { 
  return str.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); 
}
