import streamlit as st
import time 
from newspaper import Article
import openai
import os
import json
from collections import Counter


openai.api_key = st.secrets["OPENAI_API_KEY"]

with st.spinner("⏳ The app is waking up... please wait a few seconds."):
    time.sleep(2)  # simulate loading delay (2–3 seconds is enough)
    
st.title("📊 EconoBot: Economic News Summarizer")
st.write("Paste a news article URL to get a plain-English summary of economic themes.")

for key in ["summary", "article_url", "content", "history"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "history" else None

with st.sidebar:
    st.subheader("📚 Summary History")
    if st.session_state.history:
        for i, item in enumerate(reversed(st.session_state.history[-5:])):
            with st.expander(f"Article {len(st.session_state.history) - i}"):
                st.markdown(f"[{item['url']}]({item['url']})")
                st.write(item["summary"][:400] + "...")
    else:
        st.info("No summaries yet.")

    st.markdown("---")
    st.subheader("📊 Mini Dashboard")
    if st.session_state.history:
        total = len(st.session_state.history)
        sentiments = [item["sentiment"] for item in st.session_state.history]
        impact_scores = [item["impact_score"] for item in st.session_state.history if isinstance(item["impact_score"], (int, float))]
        all_topics = [t for item in st.session_state.history for t in item.get("topics", [])]
        topic_counts = Counter(all_topics).most_common(3)

        st.write(f"Articles summarized: **{total}**")
        st.write(f"Avg. Impact Score: **{round(sum(impact_scores)/len(impact_scores), 1)}**" if impact_scores else "No impact data yet")
        st.write(f" Most common sentiment: **{Counter(sentiments).most_common(1)[0][0]}**")
        st.write("Top Topics:")
        for topic, count in topic_counts:
            st.markdown(f"- **{topic}** ({count})")
    else:
        st.info("No dashboard data yet.")

url = st.text_input("🔗 Paste the URL of a news article to summarize:")
if url:
    st.session_state.article_url = url

if st.button("Summarize") and st.session_state.article_url:
    try:
        article = Article(
            st.session_state.article_url,
            browser_user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        article.download()
        article.parse()
        content = article.text
        st.session_state.content = content

        if len(content) < 300:
            st.error("Article too short or blocked. Try a different source.")
            st.stop()

        st.subheader("Article Preview")
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

        with st.spinner("Summarizing with GPT..."):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500
            )
            summary = response['choices'][0]['message']['content']
            st.session_state.summary = summary

        metadata_prompt = f"""
        From the article below, extract:
        1. The main economic topic(s) (max 2).
        2. The sentiment (Positive, Neutral, or Negative).
        3. An impact score from 1 to 10.

        Respond in JSON format like:
        {{"topics": ["Inflation", "Trade"], "sentiment": "Positive", "impact_score": 7}}

        Article:
        {content}
        """

        metadata_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": metadata_prompt}],
            temperature=0.4,
            max_tokens=150
        )
        metadata = json.loads(metadata_response['choices'][0]['message']['content'])

        st.session_state.history.append({
            "url": st.session_state.article_url,
            "summary": summary,
            "topics": metadata.get("topics", []),
            "sentiment": metadata.get("sentiment", "Unknown"),
            "impact_score": metadata.get("impact_score", 0)
        })

    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.summary:
    summary = st.session_state.summary
    content = st.session_state.content

    st.subheader("EconoBot Summary")
    st.write(summary)

    language = st.selectbox("Translate summary to another language:", ["None", "Korean", "Chinese", "Spanish", "French"])
    if language != "None":
        with st.spinner(f"Translating into {language}..."):
            translation = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Translate this into {language}:\n\n{summary}"}],
                temperature=0.5,
                max_tokens=500
            )
            translated_text = translation['choices'][0]['message']['content']
            st.subheader(f"{language} Translation")
            st.write(translated_text)

    st.subheader("Ask a Question About the Article")
    user_question = st.text_input("Enter your question:")
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
            st.markdown("**Answer:**")
            st.write(answer)

    st.download_button("Download English Summary", summary, file_name="econobot_summary.txt")