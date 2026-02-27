import streamlit as st
from pdf_assistant import (
    chat_with_assistant,
    get_all_chats_for_user,
    create_new_chat,
    get_chat_history,
    get_loaded_pdfs
)

st.set_page_config(page_title="PDF Assistant", page_icon="📄", layout="wide")

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = "streamlit_user"
if "run_id" not in st.session_state:
    st.session_state.run_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.title("📄 PDF Assistant")
    
    st.markdown("---")
    
    # New chat button - prominent
    if st.button("➕ New Conversation", use_container_width=True, type="primary"):
        st.session_state.run_id = create_new_chat(st.session_state.user_id)
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # Show loaded PDFs in current session
    if st.session_state.run_id:
        pdfs = get_loaded_pdfs(st.session_state.run_id)
        if pdfs:
            st.markdown("### 📚 PDFs in this chat")
            for pdf in pdfs:
                with st.expander(f"📄 {pdf['name']}", expanded=False):
                    st.caption(pdf['url'][:50] + "..." if len(pdf['url']) > 50 else pdf['url'])
    
    st.markdown("---")
    
    # Previous chats - always load from DB
    st.markdown("### 💬 Chat History")
    chats = get_all_chats_for_user(st.session_state.user_id)
    
    if not chats:
        st.caption("No previous chats yet")
    
    for chat in chats[:15]:  # Show last 15
        # Highlight current chat
        is_current = chat["run_id"] == st.session_state.run_id
        button_label = f"{'🔵 ' if is_current else '📂 '}{chat['display_name']}"
        
        if st.button(
            button_label,
            key=f"chat_{chat['run_id']}",
            use_container_width=True,
            disabled=is_current
        ):
            st.session_state.run_id = chat["run_id"]
            # Load chat history from storage
            st.session_state.messages = get_chat_history(
                st.session_state.user_id, 
                chat["run_id"]
            )
            st.rerun()
    
    st.markdown("---")
    st.markdown("""
    ### 💡 Tips:
    - Paste any PDF link in chat
    - Add multiple PDFs to same chat
    - Ask questions about any PDF
    - Your chats are saved automatically!
    """)

# Main chat area
st.title("💬 Chat with your PDFs")

# Create new chat if none exists
if not st.session_state.run_id:
    # Check if there are existing chats
    chats = get_all_chats_for_user(st.session_state.user_id)
    if chats:
        # Load the most recent chat
        st.session_state.run_id = chats[0]["run_id"]
        st.session_state.messages = get_chat_history(
            st.session_state.user_id, 
            chats[0]["run_id"]
        )
    else:
        st.session_state.run_id = create_new_chat(st.session_state.user_id)

# Show current chat info
pdfs = get_loaded_pdfs(st.session_state.run_id)
if pdfs:
    pdf_names = ", ".join([p["name"] for p in pdfs[:3]])
    if len(pdfs) > 3:
        pdf_names += f" +{len(pdfs)-3} more"
    st.caption(f"📚 {pdf_names}")

# Display messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Initial prompt for new chats
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("""
👋 **Welcome!** 

Paste a PDF link to get started. I'll analyze it and answer your questions.

**Example:**
```
https://example.com/document.pdf
```

You can add multiple PDFs to the same chat and ask questions about any of them!
        """)

# Chat input
if prompt := st.chat_input("Paste a PDF link or ask a question..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get response
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            response = chat_with_assistant(
                st.session_state.user_id,
                st.session_state.run_id,
                prompt
            )
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()