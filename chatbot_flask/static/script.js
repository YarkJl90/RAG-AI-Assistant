// --- DICCIONARIO DE TRADUCCIONES (i18n) ---
const i18n = {
    es: {
        param_control: "Control de Parámetros",
        language_label: "Idioma de la App / IA",
        theme_label: "Tema de Color",
        profile_label: "Perfil (Persona)",
        temp_label: "Temperatura / Creatividad",
        tokens_label: "Máx Tokens (Longitud)",
        enable_rag: "Activar RAG (Docs)",
        btn_save: "Guardar Config",
        btn_clear: "Borrar Memoria",
        btn_reset: "Reset UI",
        welcome_msg: "Hola, soy Máquina KANIKI. ¿En qué puedo ayudarte hoy?",
        placeholder: "Escribe tu mensaje aquí...",
        thinking: "✨ Pensando...",
        mem_cleared: "🧠 Memoria borrada.",
        saved: "Configuración guardada.",
        reset_confirm: "¿Resetear toda la configuración?"
    },
    en: {
        param_control: "Parameter Control",
        language_label: "App / AI Language",
        theme_label: "Color Theme",
        profile_label: "Profile (Persona)",
        temp_label: "Temperature / Creativity",
        tokens_label: "Max Tokens (Length)",
        enable_rag: "Enable RAG (Docs)",
        btn_save: "Save Settings",
        btn_clear: "Clear Memory",
        btn_reset: "Reset UI",
        welcome_msg: "Hello, I am Machine KANIKI. How can I help you today?",
        placeholder: "Type your message here...",
        thinking: "✨ Thinking...",
        mem_cleared: "🧠 Memory cleared.",
        saved: "Settings saved.",
        reset_confirm: "Reset all settings?"
    },
    pt: {
        param_control: "Controle de Parâmetros",
        language_label: "Idioma do App / IA",
        theme_label: "Tema de Cores",
        profile_label: "Perfil (Persona)",
        temp_label: "Temperatura / Criatividade",
        tokens_label: "Máx Tokens (Comprimento)",
        enable_rag: "Ativar RAG (Docs)",
        btn_save: "Salvar Config",
        btn_clear: "Limpar Memória",
        btn_reset: "Resetar UI",
        welcome_msg: "Olá, sou Máquina KANIKI. Como posso ajudar hoje?",
        placeholder: "Digite sua mensagem aqui...",
        thinking: "✨ Pensando...",
        mem_cleared: "🧠 Memória limpa.",
        saved: "Configurações salvas.",
        reset_confirm: "Redefinir todas as configurações?"
    }
};

document.addEventListener("DOMContentLoaded", () => {
    
    // --- Referencias UI ---
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const openBtn = document.getElementById("open-sidebar");
    const closeBtn = document.getElementById("close-sidebar");
    
    const langSelect = document.getElementById("app-language");
    const userInput = document.getElementById("user-input");
    const typingSpan = document.querySelector("#typing-indicator span");

    // ==========================================
    // 🎨 LÓGICA DE TEMAS (COLOR SWITCHING)
    // ==========================================
    const themeBtns = document.querySelectorAll(".theme-btn");
    
    function setTheme(themeName) {
        if (themeName === 'default') {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', themeName);
        }

        themeBtns.forEach(btn => {
            if (btn.getAttribute("data-theme") === themeName) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        localStorage.setItem("kaniki_theme", themeName);
    }

    const savedTheme = localStorage.getItem("kaniki_theme") || "default";
    setTheme(savedTheme);

    themeBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const theme = btn.getAttribute("data-theme");
            setTheme(theme);
        });
    });

    // ==========================================
    // 🌐 LÓGICA DE IDIOMA
    // ==========================================
    function updateLanguage(lang) {
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.getAttribute("data-i18n");
            if (i18n[lang][key]) {
                el.textContent = i18n[lang][key];
            }
        });
        if (userInput) userInput.placeholder = i18n[lang].placeholder;
        if (typingSpan) typingSpan.textContent = i18n[lang].thinking;
        localStorage.setItem("kaniki_lang", lang);
    }

    if (langSelect) {
        const savedLang = localStorage.getItem("kaniki_lang") || "es";
        langSelect.value = savedLang;
        updateLanguage(savedLang);
        langSelect.addEventListener("change", (e) => {
            updateLanguage(e.target.value);
        });
    }

    // ==========================================
    // ↔️ LÓGICA DE SIDEBAR INTELIGENTE (FIX)
    // ==========================================
    function toggleSidebar() {
        const isMobile = window.innerWidth <= 800; // Coincide con CSS media query

        if (isMobile) {
            // En móvil: Se usa .open para mostrarlo (por defecto está oculto)
            sidebar.classList.toggle("open");
            overlay.classList.toggle("show");
        } else {
            // En escritorio: Se usa .closed para colapsarlo (por defecto está visible)
            sidebar.classList.toggle("closed");
        }
    }

    if(openBtn) openBtn.addEventListener("click", toggleSidebar);
    if(closeBtn) closeBtn.addEventListener("click", toggleSidebar);
    if(overlay) overlay.addEventListener("click", toggleSidebar);

    // --- Slider Live Values ---
    const sliders = [
        { input: "param-temperature", label: "val-temp" },
        { input: "param-frequency", label: "val-freq" },
        { input: "param-presence", label: "val-pres" }
    ];

    sliders.forEach(item => {
        const el = document.getElementById(item.input);
        const lab = document.getElementById(item.label);
        if(el && lab) {
            el.addEventListener("input", (e) => lab.textContent = e.target.value);
        }
    });

    // --- Chat Logic ---
    const sendBtn = document.getElementById("send-btn");
    
    sendBtn.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (e) => {
        if(e.key === "Enter") sendMessage();
    });

    document.getElementById("btn-clear-memory").addEventListener("click", () => {
        const currentLang = document.getElementById("app-language").value;
        fetch("/reset", { method: "POST" })
            .then(res => res.json())
            .then(() => alert(i18n[currentLang].mem_cleared));
    });

    document.getElementById("btn-reset-ui").addEventListener("click", () => {
        const currentLang = document.getElementById("app-language").value;
        if(confirm(i18n[currentLang].reset_confirm)) {
            localStorage.removeItem("kaniki_lang");
            localStorage.removeItem("kaniki_theme");
            window.location.reload();
        }
    });
    
    document.getElementById("btn-save-settings").addEventListener("click", () => {
        const currentLang = document.getElementById("app-language").value;
        alert(i18n[currentLang].saved);
    });
});

// --- RECOLECTAR PARÁMETROS ---
function getModelParameters() {
    return {
        model: document.getElementById("param-model").value,
        profile: document.getElementById("param-profile").value,
        temperature: parseFloat(document.getElementById("param-temperature").value),
        max_tokens: parseInt(document.getElementById("param-max-tokens").value),
        frequency_penalty: parseFloat(document.getElementById("param-frequency").value),
        presence_penalty: parseFloat(document.getElementById("param-presence").value),
        rag_enabled: document.getElementById("rag-enabled").checked,
        rag_topk: parseInt(document.getElementById("rag-topk").value),
        rag_depth: parseInt(document.getElementById("rag-depth").value),
        language: document.getElementById("app-language").value 
    };
}

function sendMessage() {
    const input = document.getElementById("user-input");
    const text = input.value.trim();
    if (!text) return;

    // Mensaje del usuario (Instantáneo)
    addMessage(text, "user-message");
    input.value = "";

    const typing = document.getElementById("typing-indicator");
    typing.style.display = "flex";
    
    const container = document.getElementById("chat-container");
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });

    const params = getModelParameters();

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: text,
            model_params: params
        }),
    })
    .then((res) => {
        if (!res.ok) {
            return res.json().then(errData => {
                throw new Error(errData.reply || "Error en servidor");
            });
        }
        return res.json();
    })
    .then((data) => {
        typing.style.display = "none";
        // Mensaje del bot con EFECTO DE ESCRITURA (animate = true)
        addMessage(data.reply, "bot-message", true, true);
    })
    .catch((err) => {
        typing.style.display = "none";
        addMessage(`⚠️ Error: ${err.message}`, "bot-message");
    });
}

// 🔥 FUNCIÓN PREMIUM: EFECTO TYPEWRITER 🔥
async function typeWriterHTML(element, html) {
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = html;

    async function typeNode(node, target) {
        if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent;
            for (let i = 0; i < text.length; i++) {
                target.textContent += text[i];
                const container = document.getElementById("chat-container");
                container.scrollTop = container.scrollHeight;
                
                await new Promise(resolve => setTimeout(resolve, 10)); 
            }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            const newElement = document.createElement(node.tagName);
            Array.from(node.attributes).forEach(attr => {
                newElement.setAttribute(attr.name, attr.value);
            });
            target.appendChild(newElement);
            
            const childNodes = Array.from(node.childNodes);
            for (const child of childNodes) {
                await typeNode(child, newElement);
            }
        }
    }

    const childNodes = Array.from(tempDiv.childNodes);
    for (const node of childNodes) {
        await typeNode(node, element);
    }
}

// --- ADD MESSAGE ACTUALIZADO ---
function addMessage(text, className, isHTML = false, animate = false) {
    const container = document.getElementById("chat-container");
    const div = document.createElement("div");
    div.className = `message ${className}`;
    
    container.appendChild(div);

    if (animate && isHTML) {
        div.classList.add("cursor-blink"); 
        typeWriterHTML(div, text).then(() => {
            div.classList.remove("cursor-blink"); 
        });
    } else {
        if (isHTML) {
            div.innerHTML = text;
        } else {
            div.textContent = text;
        }
    }
    
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
}