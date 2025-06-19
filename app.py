import streamlit as st
from newspaper import Article
import openai
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Title
st.title("📊 EconoBot: Economic News Summarizer")
st.write("Paste a news article URL to get a plain-English summary of economic themes.")

# Sidebar History Panel
with st.sidebar:
    st.subheader("📚 Summary History")
    if "history" in st.session_state and st.session_state.history:
        for i, item in enumerate(reversed(st.session_state.history[-5:])):
            with st.expander(f"Article {len(st.session_state.history) - i}"):
                st.markdown(f"🔗 [{item['url']}]({item['url']})")
                st.write(item["summary"][:500] + "...")
    else:
        st.info("No summaries yet.")

# Input URL
url = st.text_input("🔗 Paste the URL of a news article to summarize:")

# Session state setup
if "summary" not in st.session_state:
    st.session_state.summary = None
if "article_url" not in st.session_state:
    st.session_state.article_url = None
if "content" not in st.session_state:
    st.session_state.content = None
if "history" not in st.session_state:
    st.session_state.history = []

if url:
    st.session_state.article_url = url

# Summarize logic
if st.button("Summarize") and st.session_state.article_url:
    try:
        article = Article(st.session_state.article_url)
        article.download()
        article.parse()
        content = article.text
        st.session_state.content = content

        if len(content) < 300:
            st.error("❌ Article too short or blocked. Try a different source.")
            st.stop()

        st.subheader("📰 Article Preview")
        st.write(content[:700] + "...")

        prompt = f"""
        You are an economic analyst. Do the following based on the article:

        1. Write a short paragraph summarizing the article's main economic themes.
        2. List 3–5 key takeaways in bullet point format.
        3. At the end, provide:
            a) The overall economic sentiment (Positive, Neutral, or Negative), labeled as 'Sentiment:'
            b) An impact score from 1 (low significance) to 10 (high significance), labeled as 'Impact Score:'

        Article:
        {content}
        """

        with st.spinner("🧠 Summarizing with GPT..."):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500
            )
            st.session_state.summary = response['choices'][0]['message']['content']

        # Save to history
        st.session_state.history.append({
            "url": st.session_state.article_url,
            "summary": st.session_state.summary
        })

    except Exception as e:
        st.error(f"⚠️ Error: {e}")

# Display summary and extras
if st.session_state.summary:
    summary = st.session_state.summary
    content = st.session_state.content

    st.subheader("💬 EconoBot Summary")
    st.write(summary)

    # 🌍 Translation
    language = st.selectbox("🌍 Translate summary to another language:", ["None", "Korean", "Chinese", "Spanish", "French"])
    if language != "None":
        with st.spinner(f"🔄 Translating into {language}..."):
            translation = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Translate this into {language}:\n\n{summary}"}],
                temperature=0.5,
                max_tokens=500
            )
            translated_text = translation['choices'][0]['message']['content']
            st.subheader(f"🌐 {language} Translation")
            st.write(translated_text)

    # 🧠 Ask a Question
    st.subheader("🧠 Ask a Question About the Article")
    user_question = st.text_input("❓ Enter your question:")
    if user_question and content:
        with st.spinner("Thinking..."):
            question_prompt = f"""
            Based on the following article, answer the user's question accurately and concisely.

            Article:
            {content}

            Question:
            {user_question}
            """
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question_prompt}],
                temperature=0.3,
                max_tokens=300
            )
            answer = response['choices'][0]['message']['content']
            st.markdown("🧾 **Answer:**")
            st.write(answer)

    # 📄 Download button
    st.download_button("📄 Download English Summary", summary, file_name="econobot_summary.txt")
