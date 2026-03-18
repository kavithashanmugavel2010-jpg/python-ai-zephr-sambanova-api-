import streamlit as st
import requests
import base64
import io
import asyncio
import edge_tts
from PIL import Image
import json
import os
import streamlit.components.v1 as components

# ===============================
# 1. SYSTEM CONFIG & MEMORY
# ===============================
MEMORY_FILE = "zephr_memory.json"
st.set_page_config(page_title="Zephr Jarvis AI", page_icon="🧠", layout="wide")

def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        return []
    except: return []

def save_memory(messages):
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f, indent=2)

# ===============================
# 2. THEME ENGINE (The "Magic" Logic)
# ===============================
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>⚙️ SYSTEM DECK</h2>", unsafe_allow_html=True)
    
    # The Toggle
    theme_mode = st.toggle("Neural Theme (Dark / Light)", value=False)
    
    if theme_mode:  # --- LIGHT MODE ---
        main_bg = "#FFFFFF"
        side_bg = "#F0F2F6"
        text_col = "#000000"  # BLACK TEXT
        accent = "#0078FF"
        bubble_bg = "#E8E8E8"
        input_bg = "#FFFFFF"
    else:           # --- DARK MODE ---
        main_bg = "radial-gradient(circle at center,#000000 0%,#001f3f 60%,#000000 100%)"
        side_bg = "#000814"
        text_col = "#FFFFFF"  # WHITE TEXT
        accent = "#00C3FF"
        bubble_bg = "rgba(0,195,255,0.1)"
        input_bg = "#001F3F"

    st.markdown("---")
    persona_choice = st.selectbox("Select Neural Persona", ["Sam (Male)", "Thessa (Female)"])
    st.header("🧬 Bio-Scanner")
    uploaded_file = st.file_uploader("Upload Medical Image", type=['png', 'jpg', 'jpeg'])

# ===============================
# 3. THE GLOBAL CSS (Forces every letter)
# ===============================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

/* MAIN APP BACKGROUND */
.stApp {{
    background: {main_bg};
    color: {text_col} !important;
    font-family: 'Orbitron', sans-serif;
}}

/* GLOBAL TEXT FORCE: This targets everything */
.stApp p, .stApp span, .stApp label, .stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp li, .stApp button {{
    color: {text_col} !important;
}}

/* SIDEBAR FORCE */
[data-testid="stSidebar"] {{
    background-color: {side_bg} !important;
    border-right: 2px solid {accent};
}}

/* CHAT BUBBLE FORCE */
.stChatMessage {{
    background-color: {bubble_bg} !important;
    border: 1px solid {accent}55 !important;
    color: {text_col} !important;
}}

/* WIDGETS (Inputs, Dropdowns, Uploaders) */
div[data-baseweb="select"] > div, 
section[data-testid="stFileUploader"] button,
.stTextInput > div > div > input {{
    background-color: {input_bg} !important;
    color: {text_col} !important;
    border: 1px solid {accent} !important;
}}

/* JARVIS CORE */
.jarvis-core {{
    width: 180px; height: 180px;
    border-radius: 50%;
    border: 3px solid {accent};
    margin: auto;
    box-shadow: 0 0 20px {accent};
    transition: transform 0.05s linear;
}}

.jarvis-title {{
    text-align: center; font-size: 50px;
    color: {accent};
    text-shadow: 0 0 20px {accent};
}}
</style>
""", unsafe_allow_html=True)

# ===============================
# 4. VOICE & SYNC ENGINE
# ===============================
async def generate_voice(text, persona):
    voice_map = { "Sam (Male)": "en-US-AndrewNeural", "Thessa (Female)": "en-US-AriaNeural" }
    communicate = edge_tts.Communicate(text, voice_map[persona])
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data += chunk["data"]
    return audio_data

def autoplay_and_sync(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    sync_js = f"""
    <script>
    var audio = window.parent.document.querySelector('audio');
    var core = window.parent.document.querySelector('.jarvis-core');
    if (audio && core) {{
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var src = context.createMediaElementSource(audio);
        var analyser = context.createAnalyser();
        src.connect(analyser); analyser.connect(context.destination);
        analyser.fftSize = 256;
        var bufferLength = analyser.frequencyBinCount;
        var dataArray = new Uint8Array(bufferLength);
        function animate() {{
            requestAnimationFrame(animate);
            analyser.getByteFrequencyData(dataArray);
            var sum = 0;
            for(var i=0; i<bufferLength; i++) {{ sum += dataArray[i]; }}
            var volume = sum / bufferLength;
            core.style.transform = "scale(" + (1 + (volume / 120)) + ")";
            core.style.boxShadow = "0 0 " + (20 + (volume * 0.8)) + "px {accent}";
        }}
        animate();
    }}
    </script>
    """
    st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    components.html(sync_js, height=0)

# ===============================
# 5. AI ENGINE (SambaNova)
# ===============================
def zephr_ai(messages, persona, image_b64=None):
    API_KEY = "YOUR_SAMBANOVA_API_KEY"
    url = "https://api.sambanova.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    system_msg = {"role": "system", "content": f"You are Zephr by Sarvesh. Persona: {persona}."}
    api_messages = [system_msg] + messages
    if image_b64:
        api_messages[-1]["content"] = [{"type": "text", "text": messages[-1]["content"]}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]
    payload = {"model": "Llama-3.2-11B-Vision-Instruct", "messages": api_messages, "temperature": 0.1}
    try:
        r = requests.post(url, headers=headers, json=payload)
        return r.json()["choices"][0]["message"]["content"]
    except: return "⚠ Neural Link Error. Check API Key."

# ===============================
# 6. UI EXECUTION
# ===============================
st.markdown('<div class="jarvis-title">ZEPHR AI</div>', unsafe_allow_html=True)
st.markdown('<div class="jarvis-core"></div>', unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = load_memory()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Enter biometric query..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    img_b64 = None
    if uploaded_file:
        img = Image.open(uploaded_file).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

    with st.spinner("⚡ Thinking..."):
        answer = zephr_ai(st.session_state.messages, persona_choice, img_b64)
    
    with st.chat_message("assistant"):
        st.markdown(answer)
        audio_bytes = asyncio.run(generate_voice(answer, persona_choice))
        autoplay_and_sync(audio_bytes)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_memory(st.session_state.messages)