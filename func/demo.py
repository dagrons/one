import numpy as np
import pandas as pd
import psutil
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid
from streamlit_ace import st_ace
from streamlit_modal import Modal


@st.experimental_fragment()
def update_cpu_percentage(placeholder):
    with placeholder.container():
        col1, col2 = st.columns(2)
        with col1:
            st.metric("CPU Percentage", f"{psutil.cpu_percent()}")
        with col2:
            st.metric("Mem Percentage", f"{psutil.virtual_memory()[2]}")


@st.experimental_fragment()
def update_point_chart(placeholder):
    if st.session_state.chart_type == 'a':
        chart_data = pd.DataFrame(np.random.randn(200, 3), columns=["a", "b", "c"])
        st.vega_lite_chart(
            chart_data,
            {
                "mark": {"type": "circle", "tooltip": True},
                "encoding": {
                    "x": {"field": "a", "type": "quantitative"},
                    "y": {"field": "b", "type": "quantitative"},
                    "size": {"field": "c", "type": "quantitative"},
                    "color": {"field": "c", "type": "quantitative"},
                },
            },
        )
    else:
        chart_data = pd.DataFrame(np.random.randn(10, 2), columns=["a", "b"])
        st.vega_lite_chart(
            chart_data,
            {
                "mark": "line",
                "encoding": {
                    "x": {"field": "a", "type": "quantitative"},
                    "y": {"field": "b", "type": "quantitative"}
                }
            }
        )


def demo_page():
    if 'chart_type' not in st.session_state:
        st.session_state.chart_type = 'a'
    st.markdown("""
    # Streamlit 
    
    st适合数据单向依赖的组件，不适合双向依赖的组件，因为双向依赖就会用到很多rerun
    """)

    common_widget_tab, metrics_tab, chart_tab, graphviz_tab, code_editor_tab, aggrid_tab = st.tabs(['常用组件', '仪表盘', '图表', 'Graphviz', '代码编辑器', 'AgGrid'])

    with common_widget_tab:
        st.markdown("## 输入")
        st.markdown("### multiselect")
        st.multiselect(
            'What are your favorite colors',
            ['Green', 'Yellow', 'Red', 'Blue'],
            ['Yellow', 'Red'])
        st.markdown("### select_slider")
        st.select_slider("", options=['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet'])
        st.markdown("""
        ## 容器
        """)
        st.markdown("""
        ### empty
        empty是一个容器，只能用来存放一个组件，每次调用都会更换组件
        如果要存放多个组件，可以这样
        ```python
        placeholder = st.empty()
        with placeholder.container():
            st.markdown("...")
            st.write("...")
        ```
        值得注意的是，每次调用`with placeholder.container()`，都会容器中之前的组件清空，**而`st.container`则不会清空之前的组件，注意两者区别**        
        """)
        st.markdown("### expander")
        with st.expander("demo expander"):
            st.markdown("...")
            st.image("img/one.png")
        st.markdown("""
        ### popover        
        """)
        with st.popover("popover"):
            password = st.text_input("请输入密码")
            if password == "dagrons":
                st.balloons()
            st.markdown("...")
    with metrics_tab:
        st.markdown("""
        # 仪表盘
        可以通过`run_every`参数实现动态刷新
        """)
        placeholder = st.empty()
        update_cpu_percentage(placeholder)
    with chart_tab:
        st.markdown("""
        # 图表                
        """)
        col1, col2 = st.columns([3, 1])
        with col2:
            chart_type = st.selectbox("图表类型", options=['a', 'b'])
            st.session_state.chart_type = chart_type
        with col1:
            placeholder = st.empty()
            update_point_chart(placeholder)
        st.markdown("""
        # pydeck
        """)
        chart_data = pd.DataFrame(
            np.random.randn(1000, 2) / [50, 50] + [37.76, -122.4],
            columns=['lat', 'lon'])

        st.pydeck_chart(pdk.Deck(
            map_style=None,
            initial_view_state=pdk.ViewState(
                latitude=37.76,
                longitude=-122.4,
                zoom=11,
                pitch=50,
            ),
            layers=[
                pdk.Layer(
                    'HexagonLayer',
                    data=chart_data,
                    get_position='[lon, lat]',
                    radius=200,
                    elevation_scale=4,
                    elevation_range=[0, 1000],
                    pickable=True,
                    extruded=True,
                ),
                pdk.Layer(
                    'ScatterplotLayer',
                    data=chart_data,
                    get_position='[lon, lat]',
                    get_color='[200, 30, 0, 160]',
                    get_radius=200,
                ),
            ],
        ))

    with graphviz_tab:
        st.markdown("""
        # Graphviz        
        用于演示图相关的算法
        """)
        st.graphviz_chart('''
                    digraph G {
                        1 -> intr[color="red"]
                        intr -> runbl
                        runbl -> 1
                        1 -> kernel
                        kernel -> zombie
                        kernel -> sleep
                        kernel -> runmem
                        sleep -> swap
                        swap -> runswap
                        runswap -> new
                        runswap -> runmem
                        new -> runmem
                        sleep -> runmem
                    }''')

    with code_editor_tab:
        st.markdown("""
        # 代码编辑器
        """)
        st_ace(language="python", keybinding="emacs")
    with aggrid_tab:
        df = pd.read_csv(
            'https://raw.githubusercontent.com/fivethirtyeight/data/master/airline-safety/airline-safety.csv')
        AgGrid(df)



