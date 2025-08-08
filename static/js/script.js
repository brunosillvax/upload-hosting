const uploadForm = document.getElementById('upload-form');
const fileInput = document.getElementById('file');
const feedback = document.getElementById('upload-feedback');
const searchInput = document.getElementById('search');
const filesList = document.getElementById('files-list-ul');
const darkModeToggle = document.getElementById('toggle-dark-mode');
const debugTerminal = document.getElementById('debug-terminal');

// 🧠 Terminal debug logger
function debugLog(msg) {
  if (!debugTerminal) return;
  const timestamp = new Date().toLocaleTimeString();
  debugTerminal.textContent += `[${timestamp}] ${msg}\n`;
  debugTerminal.scrollTop = debugTerminal.scrollHeight;
}

// Validação simples no envio do formulário
uploadForm?.addEventListener('submit', function (e) {
  if (!fileInput.value) {
    e.preventDefault();
    feedback.textContent = 'Por favor, selecione ao menos um arquivo antes de enviar.';
    feedback.style.color = 'red';
    debugLog('⚠️ Tentativa de envio sem arquivo.');
    return;
  }
  feedback.textContent = 'Enviando arquivo(s)...';
  feedback.style.color = 'black';
  debugLog(`📤 Enviando ${fileInput.files.length} arquivo(s)...`);
});

// Delegação de eventos para copiar link e excluir arquivo
filesList?.addEventListener('click', async function (e) {
  const target = e.target;

  // Botão copiar link
  if (target.classList.contains('copy-btn')) {
    const link = target.dataset.link;
    if (!link) return;

    try {
      await navigator.clipboard.writeText(link);
      showCopyMessage(target, 'Link copiado!');
      debugLog(`📋 Copiado: ${link}`);
    } catch {
      showCopyMessage(target, 'Erro ao copiar');
      debugLog('❌ Erro ao copiar link');
    }
  }

  // Botão excluir arquivo
  if (target.classList.contains('delete-btn')) {
  const filename = target.dataset.filename;
  if (!filename) return;

  console.log("🧪 Tentando confirmar exclusão...");
  const confirmar = confirm(`Tem certeza que deseja excluir o arquivo:\n"${filename}"?`);
  debugLog(`🗑️ Clique em apagar: ${filename} | Confirmado: ${confirmar}`);

    if (confirmar) {
      try {
        const res = await fetch(`/delete/${encodeURIComponent(filename)}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        const data = await res.json();
        debugLog(`🔁 Resposta do backend: ${JSON.stringify(data)}`);
        alert(data.message);
        if (data.status === 'success') {
          const li = target.closest('li');
          li?.remove();
          debugLog(`✅ Arquivo removido da tela: ${filename}`);
        }
      } catch (err) {
        alert('Erro ao tentar excluir o arquivo.');
        debugLog(`❌ Erro no fetch DELETE: ${err}`);
      }
    } else {
      debugLog('🚫 Exclusão cancelada pelo usuário.');
    }
  }
});

// Busca local
searchInput?.addEventListener('input', function (e) {
  const query = e.target.value.toLowerCase();
  const items = filesList?.querySelectorAll('li') || [];

  items.forEach(li => {
    const filename = li.querySelector('.filename')?.textContent.toLowerCase() || '';
    li.style.display = filename.includes(query) ? '' : 'none';
  });

  debugLog(`🔍 Busca: "${query}"`);
});

// Modo escuro
function setDarkMode(enabled) {
  document.body.classList.toggle('dark', enabled);
  darkModeToggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
  localStorage.setItem('darkMode', enabled);
  debugLog(`🌓 Modo escuro: ${enabled ? 'Ativado' : 'Desativado'}`);
}

const savedDarkMode = localStorage.getItem('darkMode');
if (savedDarkMode === 'true') {
  setDarkMode(true);
} else if (!savedDarkMode) {
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  setDarkMode(prefersDark);
}

darkModeToggle?.addEventListener('click', () => {
  const enabled = document.body.classList.contains('dark');
  setDarkMode(!enabled);
});

// Ocultar flash
window.addEventListener('DOMContentLoaded', () => {
  const flashMessages = document.getElementById('flash-messages');
  if (flashMessages) {
    setTimeout(() => {
      flashMessages.style.opacity = '0';
      setTimeout(() => flashMessages.remove(), 500);
    }, 4000);
  }
});

// Mensagem copiar
function showCopyMessage(button, message) {
  const oldMsg = button.querySelector('.copy-message');
  if (oldMsg) oldMsg.remove();

  const msg = document.createElement('span');
  msg.textContent = message;
  msg.className = 'copy-message';

  Object.assign(msg.style, {
    position: 'absolute',
    background: '#333',
    color: '#fff',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '0.85rem',
    top: '-30px',
    right: '0',
    whiteSpace: 'nowrap',
    zIndex: '1000',
    opacity: '0',
    pointerEvents: 'none',
    transition: 'opacity 0.3s ease'
  });

  button.style.position = 'relative';
  button.appendChild(msg);

  requestAnimationFrame(() => {
    msg.style.opacity = '1';
  });

  setTimeout(() => {
    msg.style.opacity = '0';
    msg.addEventListener('transitionend', () => {
      msg.remove();
    });
  }, 2000);
}
