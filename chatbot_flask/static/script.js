// --- DICCIONARIO DE TRADUCCIONES (i18n) ---
const i18n = {
    es: {
        param_control: "Control de Parámetros",
        language_label: "Idioma de la App / IA",
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
    
    // Referencias para Idioma
    const langSelect = document.getElementById("app-language");
    const userInput = document.getElementById("user-input");
    const typingSpan = document.querySelector("#typing-indicator span");

    // --- LÓGICA DE IDIOMA (NUEVO) ---
    function updateLanguage(lang) {
        // 1. Traducir textos estáticos con atributo data-i18n
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.getAttribute("data-i18n");
            if (i18n[lang][key]) {
                el.textContent = i18n[lang][key];
            }
        });

        // 2. Traducir atributos específicos (placeholder)
        if (userInput) userInput.placeholder = i18n[lang].placeholder;

        // 3. Traducir indicador de "Thinking..."
        if (typingSpan) typingSpan.textContent = i18n[lang].thinking;
        
        // 4. Guardar preferencia en el navegador
        localStorage.setItem("kaniki_lang", lang);
    }

    // Inicializar idioma (guardado o por defecto 'es')
    if (langSelect) {
        const savedLang = localStorage.getItem("kaniki_lang") || "es";
        langSelect.value = savedLang;
        updateLanguage(savedLang);

        // Evento al cambiar el selector
        langSelect.addEventListener("change", (e) => {
            updateLanguage(e.target.value);
        });
    }

    // --- Sidebar Toggle ---
    function toggleSidebar() {
        sidebar.classList.toggle("open");
        overlay.classList.toggle("show");
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

    // --- Botones Acción ---
    document.getElementById("btn-clear-memory").addEventListener("click", () => {
        const currentLang = document.getElementById("app-language").value;
        fetch("/reset", { method: "POST" })
            .then(res => res.json())
            .then(() => alert(i18n[currentLang].mem_cleared));
    });

    document.getElementById("btn-reset-ui").addEventListener("click", () => {
        const currentLang = document.getElementById("app-language").value;
        if(confirm(i18n[currentLang].reset_confirm)) {
            // Borramos preferencia y recargamos
            localStorage.removeItem("kaniki_lang");
            window.location.reload();
        }
    });
    
    document.getElementById("btn-save-settings").addEventListener("click", () => {
        const currentLang = document.getElementById("app-language").value;
        alert(i18n[currentLang].saved);
    });
});

// --- RECOLECTAR TODOS LOS PARÁMETROS (Actualizado con Idioma) ---
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
        
        // ¡IMPORTANTE! Enviamos el idioma seleccionado al backend
        language: document.getElementById("app-language").value 
    };
}

function sendMessage() {
    const input = document.getElementById("user-input");
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "user-message");
    input.value = "";

    const typing = document.getElementById("typing-indicator");
    typing.style.display = "flex";

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
        addMessage(data.reply, "bot-message", true);
    })
    .catch((err) => {
        typing.style.display = "none";
        addMessage(`⚠️ Error: ${err.message}`, "bot-message");
    });
}

function addMessage(text, className, isHTML = false) {
    const container = document.getElementById("chat-container");
    const div = document.createElement("div");
    div.className = `message ${className}`;
    
    if (isHTML) {
        div.innerHTML = text;
    } else {
        div.textContent = text;
    }
    
    container.appendChild(div);
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
}