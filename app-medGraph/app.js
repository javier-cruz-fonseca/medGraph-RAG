/* ============================================================================
   Doctor AI — Application Logic
   Connects to FastAPI backend at /chat, /sessions, /health
   ============================================================================ */

(() => {
    'use strict';

    // ─── Configuration ──────────────────────────────────────────────────────────
    const API_BASE = 'http://localhost:8089';
    const STORAGE_KEY = 'doctorai_sessions';

    // ─── DOM References ─────────────────────────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        sidebar: $('#sidebar'),
        sidebarOverlay: $('#sidebarOverlay'),
        btnMenu: $('#btnMenu'),
        btnThemeToggle: $('#btnThemeToggle'),
        btnNewChat: $('#btnNewChat'),
        sessionsList: $('#sessionsList'),
        statusIndicator: $('#statusIndicator'),
        modelInfo: $('#modelInfo'),
        headerStatus: $('#headerStatus'),
        messagesContainer: $('#messagesContainer'),
        welcomeScreen: $('#welcomeScreen'),
        messages: $('#messages'),
        messageInput: $('#messageInput'),
        btnSend: $('#btnSend'),
    };

    // ─── State ──────────────────────────────────────────────────────────────────
    let state = {
        currentSessionId: null,
        sessions: [],       // { id, label, messages: [{role, content, time}] }
        isLoading: false,
        isOnline: false,
    };


    // ─── Utilities ──────────────────────────────────────────────────────────────

    function generateId() {
        return crypto.randomUUID ? crypto.randomUUID() : 
            'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
                const r = (Math.random() * 16) | 0;
                return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
            });
    }

    function timeNow() {
        return new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /** Very lightweight Markdown → HTML (covers the most common patterns) */
    function renderMarkdown(text) {
        let html = escapeHtml(text);

        // Code blocks (``` ... ```)
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
            return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold **text**
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Italic *text*
        html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');

        // Headers
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

        // Blockquotes
        html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

        // Unordered lists
        html = html.replace(/^[*-] (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
        // Collapse consecutive <ul> tags
        html = html.replace(/<\/ul>\s*<ul>/g, '');

        // Ordered lists
        html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

        // Line breaks (preserve paragraph structure)
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');
        html = '<p>' + html + '</p>';

        // Clean up empty paragraphs
        html = html.replace(/<p>\s*<\/p>/g, '');
        html = html.replace(/<p>\s*(<h[1-3]>)/g, '$1');
        html = html.replace(/(<\/h[1-3]>)\s*<\/p>/g, '$1');
        html = html.replace(/<p>\s*(<pre>)/g, '$1');
        html = html.replace(/(<\/pre>)\s*<\/p>/g, '$1');
        html = html.replace(/<p>\s*(<ul>)/g, '$1');
        html = html.replace(/(<\/ul>)\s*<\/p>/g, '$1');
        html = html.replace(/<p>\s*(<blockquote>)/g, '$1');
        html = html.replace(/(<\/blockquote>)\s*<\/p>/g, '$1');

        return html;
    }


    // ─── Persistence ────────────────────────────────────────────────────────────

    function saveSessions() {
        try {
            const data = state.sessions.map(s => ({
                id: s.id,
                label: s.label,
                messages: s.messages.slice(-100), // keep last 100 messages
            }));
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch {
            // storage full — silently fail
        }
    }

    function loadSessions() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                state.sessions = JSON.parse(raw);
            }
        } catch {
            state.sessions = [];
        }
    }


    // ─── Theme Management ───────────────────────────────────────────────────────

    function initTheme() {
        const savedTheme = localStorage.getItem('doctorai_theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('doctorai_theme', newTheme);
    }


    // ─── API Calls ──────────────────────────────────────────────────────────────

    async function apiHealthCheck() {
        try {
            const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
            if (!res.ok) throw new Error();
            const data = await res.json();
            setOnlineStatus(true, data.model);
            return true;
        } catch {
            setOnlineStatus(false);
            return false;
        }
    }

    async function apiChat(message, sessionId) {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Error ${res.status}`);
        }

        return res.json();
    }

    async function apiDeleteSession(sessionId) {
        try {
            await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
        } catch {
            // best effort
        }
    }


    // ─── UI Updates ─────────────────────────────────────────────────────────────

    function setOnlineStatus(online, model) {
        state.isOnline = online;
        const dot = dom.statusIndicator.querySelector('.status-dot');
        const label = dom.statusIndicator.querySelector('span');

        dot.classList.remove('online', 'error');

        if (online) {
            dot.classList.add('online');
            label.textContent = 'Conectado';
            dom.modelInfo.textContent = model || '—';
            dom.headerStatus.textContent = 'Asistente Médico · En línea';
        } else {
            dot.classList.add('error');
            label.textContent = 'Desconectado';
            dom.modelInfo.textContent = '—';
            dom.headerStatus.textContent = 'Asistente Médico · Sin conexión';
        }
    }

    function renderSessionsList() {
        if (state.sessions.length === 0) {
            dom.sessionsList.innerHTML = `
                <div class="sessions-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <p>Aún no hay conversaciones.<br>¡Empieza una nueva consulta!</p>
                </div>
            `;
            return;
        }

        dom.sessionsList.innerHTML = state.sessions.map(session => `
            <div class="session-item ${session.id === state.currentSessionId ? 'active' : ''}"
                 data-session-id="${session.id}">
                <svg class="session-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <span class="session-label">${escapeHtml(session.label)}</span>
                <button class="session-delete" data-delete-id="${session.id}" title="Eliminar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        `).join('');
    }

    function renderMessages() {
        const session = getSession(state.currentSessionId);
        if (!session || session.messages.length === 0) {
            dom.messages.innerHTML = '';
            dom.welcomeScreen.style.display = 'flex';
            return;
        }

        dom.welcomeScreen.style.display = 'none';
        dom.messages.innerHTML = session.messages.map(msg => createMessageHTML(msg)).join('');
        scrollToBottom();
    }

    function createMessageHTML(msg) {
        const isUser = msg.role === 'user';
        const avatarContent = isUser
            ? '<span>Tú</span>'
            : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                   <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
               </svg>`;

        const bubbleContent = isUser ? escapeHtml(msg.content) : renderMarkdown(msg.content);

        return `
            <div class="message ${isUser ? 'user' : 'ai'}">
                <div class="message-avatar">${avatarContent}</div>
                <div class="message-content">
                    <div class="message-bubble">${bubbleContent}</div>
                    <div class="message-time">${msg.time || ''}</div>
                </div>
            </div>
        `;
    }

    function appendMessage(msg) {
        dom.welcomeScreen.style.display = 'none';

        const temp = document.createElement('div');
        temp.innerHTML = createMessageHTML(msg);
        const el = temp.firstElementChild;
        dom.messages.appendChild(el);
        scrollToBottom();
        return el;
    }

    function showTypingIndicator() {
        const html = `
            <div class="message ai" id="typingMessage">
                <div class="message-avatar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                    </svg>
                </div>
                <div class="message-content">
                    <div class="message-bubble">
                        <div class="typing-indicator">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        const temp = document.createElement('div');
        temp.innerHTML = html;
        dom.messages.appendChild(temp.firstElementChild);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typingMessage');
        if (el) el.remove();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            dom.messagesContainer.scrollTop = dom.messagesContainer.scrollHeight;
        });
    }

    function setLoading(loading) {
        state.isLoading = loading;
        dom.btnSend.disabled = loading || !dom.messageInput.value.trim();
        dom.messageInput.disabled = loading;

        if (loading) {
            dom.messageInput.placeholder = 'Doctor AI está pensando...';
        } else {
            dom.messageInput.placeholder = 'Describe tu consulta médica...';
            dom.messageInput.focus();
        }
    }


    // ─── Session Management ─────────────────────────────────────────────────────

    function getSession(id) {
        return state.sessions.find(s => s.id === id);
    }

    function createNewSession() {
        const session = {
            id: generateId(),
            label: 'Nueva consulta',
            messages: [],
        };
        state.sessions.unshift(session);
        state.currentSessionId = session.id;
        saveSessions();
        renderSessionsList();
        renderMessages();
        closeSidebar();
        dom.messageInput.focus();
        return session;
    }

    function switchSession(id) {
        state.currentSessionId = id;
        renderSessionsList();
        renderMessages();
        closeSidebar();
    }

    function deleteSession(id) {
        apiDeleteSession(id);
        state.sessions = state.sessions.filter(s => s.id !== id);

        if (state.currentSessionId === id) {
            state.currentSessionId = state.sessions[0]?.id || null;
        }

        saveSessions();
        renderSessionsList();
        renderMessages();
    }

    function updateSessionLabel(sessionId, message) {
        const session = getSession(sessionId);
        if (session && session.label === 'Nueva consulta') {
            session.label = message.length > 40 ? message.slice(0, 40) + '…' : message;
            saveSessions();
            renderSessionsList();
        }
    }


    // ─── Core: Send Message ─────────────────────────────────────────────────────

    async function sendMessage(text) {
        if (state.isLoading || !text.trim()) return;

        // Ensure we have a session
        let session = getSession(state.currentSessionId);
        if (!session) {
            session = createNewSession();
        }

        const userMsg = { role: 'user', content: text.trim(), time: timeNow() };
        session.messages.push(userMsg);
        updateSessionLabel(session.id, text.trim());
        appendMessage(userMsg);
        saveSessions();

        // Clear input
        dom.messageInput.value = '';
        autoResizeInput();
        setLoading(true);
        showTypingIndicator();

        try {
            const data = await apiChat(text.trim(), session.id);

            removeTypingIndicator();

            // Update session id if server assigned one
            if (data.session_id && data.session_id !== session.id) {
                session.id = data.session_id;
                state.currentSessionId = data.session_id;
                saveSessions();
                renderSessionsList();
            }

            const aiMsg = { role: 'ai', content: data.response, time: timeNow() };
            session.messages.push(aiMsg);
            appendMessage(aiMsg);
            saveSessions();

        } catch (err) {
            removeTypingIndicator();

            const errMsg = {
                role: 'ai',
                content: `⚠️ **Error de conexión**: ${err.message || 'No se pudo contactar al servidor.'}. Verifica que la API esté en ejecución en \`${API_BASE}\`.`,
                time: timeNow(),
            };
            session.messages.push(errMsg);
            appendMessage(errMsg);
            saveSessions();
        }

        setLoading(false);
    }


    // ─── Sidebar Mobile ─────────────────────────────────────────────────────────

    function openSidebar() {
        dom.sidebar.classList.add('open');
        dom.sidebarOverlay.classList.add('visible');
    }

    function closeSidebar() {
        dom.sidebar.classList.remove('open');
        dom.sidebarOverlay.classList.remove('visible');
    }


    // ─── Input Auto-Resize ──────────────────────────────────────────────────────

    function autoResizeInput() {
        const textarea = dom.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';

        dom.btnSend.disabled = state.isLoading || !textarea.value.trim();
    }


    // ─── Event Listeners ────────────────────────────────────────────────────────

    function bindEvents() {
        // Send button
        dom.btnSend.addEventListener('click', () => {
            sendMessage(dom.messageInput.value);
        });

        // Input: Enter (without Shift) sends, Shift+Enter = newline
        dom.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(dom.messageInput.value);
            }
        });

        // Input auto-resize
        dom.messageInput.addEventListener('input', autoResizeInput);

        // New chat
        dom.btnNewChat.addEventListener('click', createNewSession);

        // Theme toggle
        if (dom.btnThemeToggle) {
            dom.btnThemeToggle.addEventListener('click', toggleTheme);
        }

        // Sidebar toggle (mobile)
        dom.btnMenu.addEventListener('click', openSidebar);
        dom.sidebarOverlay.addEventListener('click', closeSidebar);

        // Sessions list (delegation)
        dom.sessionsList.addEventListener('click', (e) => {
            // Delete button
            const deleteBtn = e.target.closest('[data-delete-id]');
            if (deleteBtn) {
                e.stopPropagation();
                const id = deleteBtn.dataset.deleteId;
                deleteSession(id);
                return;
            }

            // Session item
            const item = e.target.closest('[data-session-id]');
            if (item) {
                switchSession(item.dataset.sessionId);
            }
        });

        // Suggestion chips
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const text = chip.dataset.suggestion;
                if (text) sendMessage(text);
            });
        });

        // Keyboard shortcut: Escape closes sidebar
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeSidebar();
        });
    }


    // ─── Init ───────────────────────────────────────────────────────────────────

    async function init() {
        initTheme();
        loadSessions();

        // Restore last session or show welcome
        if (state.sessions.length > 0) {
            state.currentSessionId = state.sessions[0].id;
        }

        renderSessionsList();
        renderMessages();
        bindEvents();

        // Health check
        await apiHealthCheck();

        // Periodic health check every 30 seconds
        setInterval(apiHealthCheck, 30000);

        // Focus input
        dom.messageInput.focus();
    }

    // Boot
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
