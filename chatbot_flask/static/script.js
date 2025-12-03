//--------------------------------------------------
// Inicialización
//--------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    // Conectar el botón SEND
document.getElementById("send-btn").addEventListener("click", sendMessage);

// Enviar con Enter
document.getElementById("user-input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});


    //--------------------------------------------------
    // Referencias del DOM
    //--------------------------------------------------
    const openBtn = document.getElementById("open-sidebar");
    const closeBtn = document.getElementById("close-sidebar");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("settings-overlay");

    const tempSlider = document.getElementById("param-temperature");
    const freqSlider = document.getElementById("param-frequency");
    const presSlider = document.getElementById("param-presence");

    const tempLabel = document.getElementById("param-temperature-value");
    const freqLabel = document.getElementById("param-frequency-value");
    const presLabel = document.getElementById("param-presence-value");

    const toggleMemory = document.getElementById("toggle-memory");
    const toggleTheme = document.getElementById("toggle-theme");
    const ragEnabled = document.getElementById("rag-enabled");

    const btnClearMemory = document.getElementById("btn-clear-memory");
    const btnSaveSettings = document.getElementById("btn-save-settings");
    const btnResetUI = document.getElementById("btn-reset-ui");


    //--------------------------------------------------
    // Sidebar Overlay (Abrir/Cerrar)
    //--------------------------------------------------
    function openSidebar() {
        sidebar.classList.add("open");
        overlay.classList.add("show");
        document.body.classList.add("settings-open");
    }

    function closeSidebarPanel() {
        sidebar.classList.remove("open");
        overlay.classList.remove("show");
        document.body.classList.remove("settings-open");
    }

    if (openBtn) openBtn.addEventListener("click", openSidebar);
    if (closeBtn) closeBtn.addEventListener("click", closeSidebarPanel);
    if (overlay) overlay.addEventListener("click", closeSidebarPanel);


    //--------------------------------------------------
    // Actualización dinámica de sliders
    //--------------------------------------------------
    if (tempSlider && tempLabel) {
        tempLabel.textContent = tempSlider.value;
        tempSlider.addEventListener("input", () => {
            tempLabel.textContent = tempSlider.value;
        });
    }

    if (freqSlider && freqLabel) {
        freqLabel.textContent = freqSlider.value;
        freqSlider.addEventListener("input", () => {
            freqLabel.textContent = freqSlider.value;
        });
    }

    if (presSlider && presLabel) {
        presLabel.textContent = presSlider.value;
        presSlider.addEventListener("input", () => {
            presLabel.textContent = presSlider.value;
        });
    }


    //--------------------------------------------------
    // Tema (Dark / Light)
    //--------------------------------------------------
    if (toggleTheme) {
        toggleTheme.addEventListener("change", () => {
            const darkMode = toggleTheme.checked;
            document.body.classList.toggle("dark-mode", darkMode);
            localStorage.setItem("kaniki_theme", darkMode ? "dark" : "light");
        });

        // Cargar tema guardado
        const savedTheme = localStorage.getItem("kaniki_theme");
        if (savedTheme === "dark") {
            toggleTheme.checked = true;
            document.body.classList.add("dark-mode");
        }
    }


    //--------------------------------------------------
    // Memory ON/OFF
    //--------------------------------------------------
    if (toggleMemory) {
        toggleMemory.addEventListener("change", () => {
            const status = toggleMemory.checked ? "on" : "off";
            localStorage.setItem("kaniki_memory", status);
        });

        const savedMemory = localStorage.getItem("kaniki_memory");
        if (savedMemory === "off") {
            toggleMemory.checked = false;
        }
    }


    //--------------------------------------------------
    // Clear Memory (Flask /reset)
    //--------------------------------------------------
    if (btnClearMemory) {
        btnClearMemory.addEventListener("click", () => {
            fetch("/reset", { method: "POST" })
                .then((res) => res.json())
                .then(() => alert("Memory cleared."))
                .catch(() => alert("Error clearing memory."));
        });
    }


    //--------------------------------------------------
    // Save Settings (localStorage)
    //--------------------------------------------------
    if (btnSaveSettings) {
        btnSaveSettings.addEventListener("click", () => {
            const settings = getModelParameters();
            localStorage.setItem("kaniki_settings", JSON.stringify(settings));
            alert("Settings saved!");
        });

        // Load settings
        const saved = localStorage.getItem("kaniki_settings");
        if (saved) {
            const config = JSON.parse(saved);
            document.getElementById("param-model").value = config.model;
            document.getElementById("param-temperature").value = config.temperature;
            document.getElementById("param-max-tokens").value = config.max_tokens;
            document.getElementById("param-frequency").value = config.frequency_penalty;
            document.getElementById("param-presence").value = config.presence_penalty;
            document.getElementById("param-profile").value = config.profile;
        }
    }


    //--------------------------------------------------
    // Reset UI
    //--------------------------------------------------
    if (btnResetUI) {
        btnResetUI.addEventListener("click", () => {
            localStorage.clear();
            window.location.reload();
        });
    }

});


//--------------------------------------------------
// Lectura de parámetros del panel
//--------------------------------------------------
function getModelParameters() {
    return {
        model: document.getElementById("param-model").value,
        temperature: parseFloat(document.getElementById("param-temperature").value),
        max_tokens: parseInt(document.getElementById("param-max-tokens").value),
        frequency_penalty: parseFloat(document.getElementById("param-frequency").value),
        presence_penalty: parseFloat(document.getElementById("param-presence").value),
        profile: document.getElementById("param-profile").value,
        memory: document.getElementById("toggle-memory").checked,
        rag_enabled: document.getElementById("rag-enabled").checked,
        rag_depth: parseInt(document.getElementById("rag-depth").value),
        rag_topk: parseInt(document.getElementById("rag-topk").value),
    };
}


//--------------------------------------------------
// Enviar mensaje al servidor Flask
//--------------------------------------------------
function sendMessage() {
    const input = document.getElementById("user-input");
    const text = input.value.trim();
    if (!text) return;

    addUserMessage(text);
    input.value = "";

    const typing = document.getElementById("typing-indicator");
    typing.style.display = "flex";

    const params = getModelParameters();

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: text,
            model_params: params,
        }),
    })
        .then((res) => res.json())
        .then((data) => {
            typing.style.display = "none";
            addBotMessage(data.reply);
        })
        .catch(() => {
            typing.style.display = "none";
            addBotMessage("Error connecting to server.");
        });
}


//--------------------------------------------------
// Render de mensajes
//--------------------------------------------------
function addUserMessage(text) {
    const c = document.getElementById("chat-container");
    const div = document.createElement("div");
    div.className = "user-message";
    div.textContent = text;
    c.appendChild(div);
    c.scrollTop = c.scrollHeight;
}

function addBotMessage(text) {
    const c = document.getElementById("chat-container");
    const div = document.createElement("div");
    div.className = "bot-message";
    c.appendChild(div);

    let i = 0;
    const speed = 10;
    let temp = "";
    const plain = text;

    function typeWriter() {
        if (i < plain.length) {
            temp += plain[i];
            div.innerHTML = temp;
            i++;
            c.scrollTop = c.scrollHeight;
            setTimeout(typeWriter, speed);
        }
    }

    typeWriter();
}
