import os

import dotenv
import streamlit as st
from streamlit_option_menu import option_menu

from func.chore.page.mortage_caculator import mortage_caculator
from func.llm_chatbot.page.llm_chatbot import llm_chatbot_page
from func.llm_chatbot.page.retriver import retrieval_page
from func.vis.page.vis import vis

if __name__ == "__main__":
    dotenv.load_dotenv()
    st.set_page_config(
        "One",
        initial_sidebar_state="expanded",
    )

    st.markdown(r"""
    <style>
       .stDeployButton{
               visibility: hidden
       }
       #MainMenu {
               visibility: hidden
       }
    </style>

    """, unsafe_allow_html=True)

    pages = {
        "QA问答": {
            "func": llm_chatbot_page,
        },
        "知识库检索": {
            "func": retrieval_page,
        },
        "房贷计算器": {
            "func": mortage_caculator,
        },
        "图表可视化": {
            "func": vis,
        }
    }
    with st.sidebar:
        st.write(f"mode: {os.getenv('mode')}")
        st.image(
            os.path.join(
                "img", "nyan_cat.png"
            ),
            use_column_width=True
        )
        options = list(pages)
        default_index = 0
        selected_page = option_menu(
            None,
            options=options,
            default_index=default_index)
        st.markdown("""
        Keyword: 算法展示，数据可视化
        """)

    if selected_page in pages:
        pages[selected_page]['func']()
